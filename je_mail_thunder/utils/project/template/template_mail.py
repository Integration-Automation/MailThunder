"""
The files of a project's mail layer, as ``create_project_dir`` writes them: ``mail/config.py``,
``mail/triggers.py`` and one template, ``mail/templates/test_report``.
"""

mail_config_template: str = '''"""
How this project sends and reads mail. je_mail_thunder.project_mail() reads the names below; every one is
optional. The login comes from mail_thunder_content.json or the environment unless AUTH is set.
"""
from je_mail_thunder import AttachmentPolicy

# A registered provider: "google", "microsoft", "microsoft_graph", "yahoo", "icloud", "zoho", "fastmail",
# "smtp", or "file" to keep the mail on disk instead of sending it.
PROVIDER = "file"

# What a message of this project may carry.
ATTACHMENT_POLICY = AttachmentPolicy(
    max_file_size=10 * 1024 * 1024,
    max_total_size=20 * 1024 * 1024,
    max_count=10,
    allowed_extensions={"html", "pdf", "json", "csv", "txt", "log", "png", "zip"},
)

# Keep a record of every mail event in mail/audit.jsonl (True), in the file named here, or nowhere (False).
AUDIT = True
'''

mail_triggers_template: str = '''"""
What this project does when mail arrives. je_mail_thunder.project_mail() calls register(mail) once.
"""


def register(mail):
    @mail.on("message_received", filter={"subject": "[RERUN]"})
    def rerun_requested(event):
        print("rerun requested by", event.message.sender)

    @mail.on("message_failed")
    def report_not_sent(event):
        print("report not sent:", event.error)

    # Look at the inbox when mail.triggers.poll() is called; start=True watches on a background thread.
    mail.watch("INBOX", start=False)
'''

mail_template_subject: str = "[{{ project }}] {{ passed }} passed, {{ failed }} failed\n"

mail_template_text: str = '''Test report for {{ project }}

Passed: {{ passed }}
Failed: {{ failed }}
{% if failures %}

Failures:
{% for failure in failures %}
  {{ loop.index }}. {{ failure.name }}: {{ failure.reason | default("no reason given") }}
{% endfor %}
{% else %}

Everything passed.
{% endif %}
'''

mail_template_html: str = '''<h2>Test report for {{ project }}</h2>
<p><b>{{ passed }}</b> passed, <b>{{ failed }}</b> failed.</p>
{% if failures %}
<ol>
{% for failure in failures %}
  <li>{{ failure.name }}: {{ failure.reason | default("no reason given") }}</li>
{% endfor %}
</ol>
{% else %}
<p>Everything passed.</p>
{% endif %}
'''

mail_template_details: dict = {
    "variables": {
        "project": {"description": "The project the report is about"},
        "passed": {"description": "How many tests passed"},
        "failed": {"description": "How many tests failed", "default": 0},
        "failures": {"description": "A list of {name, reason} for the failed tests", "default": []},
    },
    "metadata": {"purpose": "Test run summary"},
}
