"""
Mail templates: the template language, the template model, where templates are loaded from, and sending one.
"""
import json
from dataclasses import dataclass

import pytest

from je_mail_thunder import mail_instance
from je_mail_thunder.auth.password import PasswordAuth
from je_mail_thunder.core.account import MailAccount
from je_mail_thunder.core.mail import Mail
from je_mail_thunder.core.message import MailMessage
from je_mail_thunder.templates import engine
from je_mail_thunder.templates.engine import CompiledTemplate, render_string
from je_mail_thunder.templates.loader import TemplateLoader, shared_template_directory
from je_mail_thunder.templates.template import MailTemplate, RenderedTemplate
from je_mail_thunder.utils.exception.exceptions import (
    MailThunderException,
    MailThunderMessageException,
    MailThunderProviderException,
    MailThunderTemplateException,
    TemplateContextError,
    TemplateNotFound,
    TemplateRenderError,
    TemplateSyntaxError,
)
from je_mail_thunder.utils.executor.action_executor import execute_action
from mail_fakes import RecordingSender

_AUTH = PasswordAuth("someone@example.com", "p4ss-word-secret")


@dataclass
class _Run:
    name: str
    _secret: str = "hidden"

    def describe(self):
        return "called"


# --- the language -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("source, expected", [
    ("plain text", "plain text"),
    ("Hello {{ name }}!", "Hello World!"),
    ("{{user.name}} / {{ user.roles.1 }}", "je / admin"),
    ("{{ run.name }}", "nightly"),
    ("{{ count }} {{ ratio }} {{ nothing }}|", "3 0.5 |"),
    ("{{ name | upper }} {{ name | lower }} {{ 'ab cd' | title }} [{{ '  x ' | trim }}]", "WORLD world Ab Cd [x]"),
    ("{{ user.roles | length }} {{ user.roles | join }} {{ user.roles | join(' + ') }}", "2 dev, admin dev + admin"),
    ("{{ missing | default('none') }} {{ missing | default }}| {{ name | default('x') }}", "none | World"),
    ("{{ missing | default(7) }} {{ \"say \\\"hi\\\"\" }} {{ -2 }} {{ 1.5 }}", '7 say "hi" -2 1.5'),
    ("{# nothing #}a{#\n multi\n line #}b", "ab"),
])
def test_values_filters_and_comments(source, expected):
    context = {"name": "World", "user": {"name": "je", "roles": ["dev", "admin"]}, "run": _Run("nightly"),
               "count": 3, "ratio": 0.5, "nothing": None}
    assert render_string(source, context) == expected


@pytest.mark.parametrize("source, expected", [
    ("{% if failed %}bad{% else %}good{% endif %}", "bad"),
    ("{% if not failed %}good{% endif %}|", "|"),
    ("{% if missing %}yes{% else %}no{% endif %}", "no"),
    ("{% if failed > 1 %}many{% elif failed == 1 %}one{% else %}none{% endif %}", "many"),
    ("{% if passed >= 10 %}a{% endif %}{% if passed < 10 %}b{% endif %}{% if passed <= 10 %}c{% endif %}", "ac"),
    ("{% if status == 'ok' %}fine{% endif %}{% if status != \"ok\" %}broken{% endif %}", "broken"),
    ("{% if not status == 'ok' %}not ok{% endif %}", "not ok"),
    ("{% if flag == true %}t{% endif %}{% if nothing == none %}n{% endif %}{% if flag != false %}f{% endif %}", "tnf"),
    ("{% if missing == none %}absent{% endif %}", "absent"),
])
def test_conditions(source, expected):
    context = {"failed": 2, "passed": 10, "status": "failed", "flag": True, "nothing": None}
    assert render_string(source, context) == expected


def test_loops_and_the_line_break_after_a_block_tag():
    source = ("Failures:\n"
              "{% for test in failures %}\n"
              "{{ loop.index }}/{{ loop.length }} {{ test.name }}{% if loop.first %} (first){% endif %}"
              "{% if loop.last %} (last){% endif %}\n"
              "{% for tag in test.tags %}\n"
              "  - {{ tag }}\n"
              "{% endfor %}\n"
              "{% endfor %}\n"
              "Done\r\n"
              "{% if none %}\r\nnever\r\n{% endif %}\r\n"
              "End")
    failures = [{"name": "login", "tags": ["api", "slow"]}, {"name": "logout", "tags": ()}]
    assert render_string(source, {"failures": failures}) == (
        "Failures:\n1/2 login (first)\n  - api\n  - slow\n2/2 logout (last)\nDone\r\nEnd")
    assert render_string("{% for key in mapping %}{{ key }}{% endfor %}", {"mapping": {"a": 1, "b": 2}}) == "ab"
    assert render_string("{% for x in items %}{{ x }}{% endfor %}|", {"items": []}) == "|"


def test_a_template_only_reads_plain_values():
    context = {"run": _Run("nightly"), "text": "abc"}
    for source in ("{{ run._secret }}", "{{ run.describe }}", "{{ run.__class__ }}", "{{ text.upper }}",
                   "{{ run.name.0 }}", "{{ missing }}", "{{ run.other }}", "{{ items.9 }}"):
        with pytest.raises(TemplateContextError):
            render_string(source, {**context, "items": [1]})
    assert render_string("{{ run._secret | default('no') }}", context) == "no"


def test_an_undefined_name_is_named():
    with pytest.raises(TemplateContextError) as raised:
        render_string("{{ user.email }}", {"user": {}})
    assert raised.value.missing == ("user.email",)
    assert isinstance(raised.value, MailThunderTemplateException) and isinstance(raised.value, MailThunderException)
    with pytest.raises(TemplateContextError):
        render_string("{% for x in missing %}{% endfor %}", {})
    assert render_string("{{ missing | upper | default('fallback') }}") == "fallback"


@pytest.mark.parametrize("source, message", [
    ("{% if x %}no end", "missing {% endif %}"),
    ("{% for x in items %}no end", "missing {% endfor %}"),
    ("{% for x of items %}{% endfor %}", "a loop is written: for item in items"),
    ("{% include 'other' %}", "unknown tag 'include'"),
    ("{% endif %}", "unknown tag 'endif'"),
    ("{{ }}", "a value is missing"),
    ("{{ | upper }}", "a value is missing"),
    ("{{ name | shout }}", "unknown filter 'shout'"),
    ("{{ name | default('x' }}", "missing its \\)"),
    ("{{ name | default(other) }}", "a filter argument is"),
    ("{{ name upper }}", "cannot read 'upper'"),
    ("{{ name | }}", "cannot read"),
    ("{{ a + b }}", "cannot read"),
    ("line one\n{{ ok }}\n{% if a %}\n{{ $ }}", "line 4"),
])
def test_what_is_not_template_syntax(source, message):
    with pytest.raises(TemplateSyntaxError, match=message):
        CompiledTemplate(source)
    with pytest.raises(TemplateSyntaxError, match="a template is text"):
        CompiledTemplate(None)


@pytest.mark.parametrize("source, context, message", [
    ("{{ count | length }}", {"count": 3}, "the filter 'length' cannot be applied to 'count'"),
    ("{{ count | join }}", {"count": 3}, "the filter 'join'"),
    ("{% if count > name %}{% endif %}", {"count": 3, "name": "x"}, "cannot compare 'count' > 'name'"),
    ("{% for x in count %}{% endfor %}", {"count": 3}, "'count' is not a list"),
    ("{% for x in name %}{% endfor %}", {"name": "text"}, "'name' is not a list"),
])
def test_values_that_do_not_fit(source, context, message):
    with pytest.raises(TemplateRenderError, match=message):
        render_string(source, context)


def test_html_output_is_escaped_unless_marked_safe():
    context = {"name": "<script>alert('x')</script> & \"co\"", "bold": "<b>ok</b>"}
    source = "<p>{{ name }}</p>{{ bold | safe }}{{ '<i>' }}"
    assert render_string(source, context, autoescape=True) == (
        "<p>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; &quot;co&quot;</p><b>ok</b>&lt;i&gt;")
    assert render_string(source, context) == f"<p>{context['name']}</p><b>ok</b><i>"


def test_a_rendering_cannot_grow_without_limit(monkeypatch):
    monkeypatch.setattr(engine, "MAX_OUTPUT_CHARACTERS", 50)
    with pytest.raises(TemplateRenderError, match="over 50 characters"):
        render_string("{% for x in items %}0123456789{% endfor %}", {"items": list(range(6))})


def test_the_names_a_template_reads():
    compiled = CompiledTemplate(
        "{{ project }} {% if failed > limit %}{% for test in failures %}{{ test.name }} {{ loop.index }} {{ owner }}"
        "{% endfor %}{% endif %}{{ note | default('') }}")
    assert compiled.names == {"project", "failed", "limit", "failures", "owner", "note"}
    assert compiled.render({"project": "p", "failed": 0, "limit": 1}) == "p "


# --- the model --------------------------------------------------------------------------------------------------

def _report(**overrides):
    values = {
        "subject": "[{{ project }}] {{ passed }} passed, {{ failed }} failed\n",
        "text": "Project {{ project }}: {{ note }}",
        "html": "<h1>{{ project }}</h1><p>{{ note }}</p>",
        "variables": {"project": {"description": "The project's name"}, "passed": {}, "failed": {"default": 0},
                      "note": {"default": ""}},
        "metadata": {"owner": "qa"},
    }
    values.update(overrides)
    return MailTemplate.from_mapping("test_report", values)


def test_a_template_renders_its_three_parts():
    rendered = _report().render({"project": "API <Testka>", "passed": 98, "failed": 2, "note": "a & b"})
    assert rendered == RenderedTemplate(
        subject="[API <Testka>] 98 passed, 2 failed", text="Project API <Testka>: a & b",
        html="<h1>API &lt;Testka&gt;</h1><p>a &amp; b</p>")
    assert rendered.to_dict()["subject"] == "[API <Testka>] 98 passed, 2 failed"
    only_text = MailTemplate("note", text="Hi {{ name }}").render({"name": "there"})
    assert (only_text.subject, only_text.text, only_text.html) == (None, "Hi there", None)


def test_declared_variables_are_checked_before_rendering():
    template = _report()
    assert template.render({"project": "p", "passed": 1}).subject == "[p] 1 passed, 0 failed"
    with pytest.raises(TemplateContextError) as raised:
        template.render({"note": "x"})
    assert (raised.value.missing, raised.value.template) == (("passed", "project"), "test_report")
    assert "test_report" in str(raised.value)
    with pytest.raises(MailThunderTemplateException, match="context is a mapping"):
        template.render(["project"])
    names = MailTemplate("listed", text="{{ a }}{{ b }}", variables=["a", "b"])
    assert [variable.required for variable in names.variables] == [True, True]
    with pytest.raises(TemplateContextError, match="\\['b'\\]"):
        names.render({"a": 1})


def test_an_undeclared_variable_is_reported_when_it_is_missing():
    with pytest.raises(TemplateContextError) as raised:
        MailTemplate("loose", subject="{{ title }}", text="x").render({})
    assert (raised.value.missing, raised.value.template) == (("title",), "loose")


def test_a_template_describes_itself():
    described = json.loads(json.dumps(_report().to_dict()))
    assert described["name"] == "test_report" and described["metadata"] == {"owner": "qa"}
    assert described["referenced_variables"] == ["failed", "note", "passed", "project"]
    assert described["variables"][0] == {"name": "project", "description": "The project's name", "required": True}
    assert described["variables"][2] == {"name": "failed", "description": "", "required": False, "default": 0}


@pytest.mark.parametrize("values, error, message", [
    ({}, MailThunderTemplateException, "has no subject, text or html"),
    ({"text": "{% if %}"}, TemplateSyntaxError, "the template 'bad', text"),
    ({"html": "{{ x | nope }}"}, TemplateSyntaxError, "the template 'bad', html: unknown filter"),
    ({"text": 5}, TemplateSyntaxError, "a template is text"),
    ({"text": "x", "body": "y"}, MailThunderTemplateException, "unknown keys \\['body'\\]"),
    ({"text": "x", "variables": "name"}, MailThunderTemplateException, "variables are a list"),
    (["text"], MailThunderTemplateException, "must be a JSON object"),
])
def test_a_malformed_template_is_refused(values, error, message):
    with pytest.raises(error, match=message):
        MailTemplate.from_mapping("bad", values)


# --- the loader -------------------------------------------------------------------------------------------------

def _write_json(directory, name, values):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text(json.dumps(values), encoding="utf-8")


def _write_directory(directory, name, parts, details=None):
    target = directory / name
    target.mkdir(parents=True)
    for filename, content in parts.items():
        (target / filename).write_text(content, encoding="utf-8")
    if details is not None:
        (target / "template.json").write_text(json.dumps(details), encoding="utf-8")


def test_a_template_is_one_json_file_or_a_directory(tmp_path):
    _write_json(tmp_path, "welcome", {"subject": "Hi {{ name }}", "text": "Welcome, {{ name }}."})
    _write_directory(tmp_path, "report", {"subject.txt": "報表 {{ day }}\n", "body.txt": "text {{ day }}",
                                          "body.html": "<b>{{ day }}</b>"},
                     {"variables": ["day"], "metadata": {"owner": "qa"}})
    _write_directory(tmp_path, "bare", {"body.txt": "only text"})
    (tmp_path / "notes.txt").write_text("not a template", encoding="utf-8")
    loader = TemplateLoader([tmp_path])
    assert loader.names() == ["bare", "report", "welcome"]
    assert loader.load("welcome").render({"name": "je"}).subject == "Hi je"
    report = loader.load("report")
    assert report.render({"day": "Mon"}) == RenderedTemplate("報表 Mon", "text Mon", "<b>Mon</b>")
    assert report.metadata["owner"] == "qa" and report.variables[0].name == "day"
    assert loader.load("bare").text == "only text"


def test_the_first_directory_wins_and_a_registered_template_wins_over_files(tmp_path):
    project, shared = tmp_path / "project", tmp_path / "shared"
    _write_json(project, "report", {"text": "project"})
    _write_json(shared, "report", {"text": "shared"})
    _write_json(shared, "footer", {"text": "shared footer"})
    loader = TemplateLoader([project, shared, tmp_path / "absent"])
    assert (loader.load("report").text, loader.load("footer").text) == ("project", "shared footer")
    loader.add(MailTemplate("report", text="registered"))
    assert loader.load("report").text == "registered"
    assert loader.names() == ["footer", "report"]
    with pytest.raises(MailThunderTemplateException, match="expected a MailTemplate"):
        loader.add({"text": "x"})


def test_the_default_directories_are_the_project_and_the_shared_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAIL_THUNDER_TEMPLATE_DIR", str(tmp_path / "shared"))
    assert shared_template_directory() == tmp_path / "shared"
    loader = TemplateLoader()
    assert loader.directories == (tmp_path / "mail" / "templates", tmp_path / "shared")
    _write_json(tmp_path / "mail" / "templates", "local", {"text": "from the project"})
    assert loader.load("local").text == "from the project"
    monkeypatch.delenv("MAIL_THUNDER_TEMPLATE_DIR")
    assert shared_template_directory().parts[-2:] == (".je_mail_thunder", "templates")


@pytest.mark.parametrize("name", ["../secret", "..", "a/b", "a\\b", "", ".hidden", "name\n", None, 5, "a..b"])
def test_a_template_name_is_never_a_path(name, tmp_path):
    (tmp_path / "secret.json").write_text(json.dumps({"text": "outside"}), encoding="utf-8")
    inside = tmp_path / "templates"
    inside.mkdir()
    with pytest.raises(TemplateNotFound):
        TemplateLoader([inside]).load(name)


def test_what_cannot_be_loaded(tmp_path, monkeypatch):
    loader = TemplateLoader([tmp_path])
    with pytest.raises(TemplateNotFound) as raised:
        loader.load("absent")
    assert raised.value.name == "absent" and raised.value.searched == (str(tmp_path),)
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(MailThunderTemplateException, match="not valid JSON"):
        loader.load("broken")
    _write_json(tmp_path, "listy", ["text"])
    with pytest.raises(MailThunderTemplateException, match="must be a JSON object"):
        loader.load("listy")
    _write_json(tmp_path, "big", {"text": "x" * 64})
    monkeypatch.setattr("je_mail_thunder.templates.loader.MAX_TEMPLATE_FILE_BYTES", 16)
    with pytest.raises(MailThunderTemplateException, match="over 16 bytes"):
        loader.load("big")


# --- sending a template -----------------------------------------------------------------------------------------

def _mail(loader):
    sender = RecordingSender()
    return Mail(account=MailAccount(auth=_AUTH), providers=[sender], templates=loader), sender


def _loader():
    loader = TemplateLoader([])
    loader.add(_report())
    return loader


def test_send_renders_the_template_into_the_message():
    mail, sender = _mail(_loader())
    sent = mail.send(to="qa@example.com", template="test_report",
                     context={"project": "APITestka", "passed": 98, "failed": 2, "note": "<see log>"})
    assert sender.sent == [sent]
    assert sent.subject == "[APITestka] 98 passed, 2 failed"
    assert (sent.text, sent.html) == ("Project APITestka: <see log>", "<h1>APITestka</h1><p>&lt;see log&gt;</p>")
    assert mail.render("test_report", {"project": "p", "passed": 1}).subject == "[p] 1 passed, 0 failed"


def test_a_field_given_beside_the_template_wins():
    mail, sender = _mail(_loader())
    inline = MailTemplate("inline", subject="From template", text="Body {{ n }}")
    sent = mail.send(to="qa@example.com", subject="Override", template=inline, context={"n": 1})
    assert (sent.subject, sent.text, sent.html) == ("Override", "Body 1", None)
    assert len(sender.sent) == 1


def test_a_template_that_cannot_be_rendered_sends_nothing():
    mail, sender = _mail(_loader())
    with pytest.raises(TemplateContextError, match="\\['passed', 'project'\\]"):
        mail.send(to="qa@example.com", template="test_report", context={})
    with pytest.raises(TemplateNotFound):
        mail.send(to="qa@example.com", template="absent")
    with pytest.raises(MailThunderProviderException, match="a context needs the template"):
        mail.send(to="qa@example.com", text="x", context={"a": 1})
    with pytest.raises(MailThunderProviderException, match="not both"):
        mail.send(MailMessage(to="qa@example.com", sender="a@example.com"), template="test_report")
    with pytest.raises(MailThunderMessageException, match="subject must be one line"):
        mail.send(to="qa@example.com", template="test_report",
                  context={"project": "x\r\nBcc: victim@example.com", "passed": 1})
    assert sender.sent == []
    assert Mail(provider="google", auth=_AUTH).templates.directories[0].parts[-2:] == ("mail", "templates")


def test_the_template_actions(monkeypatch):
    sender = RecordingSender()
    monkeypatch.setattr(mail_instance, "_account", MailAccount(auth=_AUTH))
    monkeypatch.setattr(mail_instance, "_providers", (sender,))
    monkeypatch.setattr(mail_instance, "templates", _loader())
    context = {"project": "APITestka", "passed": 5}
    record = execute_action([
        ["MT_mail_render_template", {"template": "test_report", "context": context}],
        ["MT_mail_send", {"to": "qa@example.com", "template": "test_report", "context": context}],
        ["MT_mail_render_template", {"template": "absent"}],
    ])
    rendered, sent, missing = record.values()
    assert rendered == {"subject": "[APITestka] 5 passed, 0 failed", "text": "Project APITestka: ",
                        "html": "<h1>APITestka</h1><p></p>"}
    assert sent["subject"] == rendered["subject"] and sender.sent[0].html == rendered["html"]
    assert "TemplateNotFound" in missing
