Mail Templates
==============

A mail template holds a subject, a text body and an HTML body that share one context, so a
report mail is written once and sent with different numbers.

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:
       mail.send(
           to="qa@example.com",
           template="test_report",
           context={"project": "APITestka", "passed": 98, "failed": 2,
                    "failures": [{"name": "login", "seconds": 1.5}]},
       )

The template renders the subject and the bodies; every other field (``to``, ``attachments``, ...)
is given as usual. A field given beside ``template=`` wins over the rendered one, so
``subject="..."`` replaces the template's subject for one mail.

----

Where Templates Live
--------------------

``Mail`` looks a template up by name, first in the project's ``mail/templates/`` directory (under
the working directory), then in the shared directory: ``~/.je_mail_thunder/templates``, or the
directory ``MAIL_THUNDER_TEMPLATE_DIR`` names.

A template is a directory:

.. code-block:: text

   mail/templates/test_report/
     subject.txt      # [{{ project }}] {{ passed }} passed, {{ failed }} failed
     body.txt         # the plain-text body
     body.html        # the HTML body
     template.json    # optional: variables and metadata

or one JSON file, ``mail/templates/test_report.json``:

.. code-block:: json

   {
     "subject": "[{{ project }}] {{ passed }} passed, {{ failed }} failed",
     "text": "Project {{ project }} finished.",
     "html": "<h1>{{ project }}</h1>",
     "variables": {
       "project": {"description": "The project's name"},
       "passed": {},
       "failed": {"default": 0}
     },
     "metadata": {"owner": "qa"}
   }

A template needs at least one of the three parts. A name is letters, digits, ``_``, ``-`` and ``.``,
never a path. To look elsewhere, give ``Mail`` its own loader:

.. code-block:: python

   from je_mail_thunder import Mail, MailTemplate, TemplateLoader

   mail = Mail(templates=TemplateLoader(["reports/templates", "/srv/shared/templates"]))
   mail.templates.add(MailTemplate("welcome", subject="Hi {{ name }}", text="Welcome, {{ name }}."))
   print(mail.templates.names())

----

The Template Language
---------------------

The syntax is the part of Jinja2 a mail needs, implemented with the standard library.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Syntax
     - Meaning
   * - ``{{ user.name }}``
     - A value. Dots reach into dicts, lists (``items.0``) and public attributes
   * - ``{{ name | upper }}``
     - A filter; several can follow each other
   * - ``{% if failed > 0 %} ... {% elif skipped %} ... {% else %} ... {% endif %}``
     - A condition: a value, ``not`` a value, or one comparison (``== != < <= > >=``) with a value,
       a text, a number, ``true``, ``false`` or ``none``
   * - ``{% for test in failures %} ... {% endfor %}``
     - A loop. Inside it, ``loop.index`` (from 1), ``loop.first``, ``loop.last`` and ``loop.length``
   * - ``{# note #}``
     - A comment

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Filter
     - Result
   * - ``upper``, ``lower``, ``title``, ``trim``
     - The text in another case, or without the spaces around it
   * - ``length``
     - The number of items
   * - ``join(", ")``
     - The items of a list as one text (``", "`` when no separator is given)
   * - ``default("none")``
     - The given value when the name is not in the context
   * - ``safe``
     - In an HTML body: output the value without escaping it

Rules worth knowing:

- A ``{% ... %}`` tag alone on its line takes the line with it, so block tags leave no blank lines.
- In the HTML body every value is HTML-escaped unless it goes through ``safe``. The subject and the
  text body are not escaped.
- A name the context does not hold is an error where it is output, and counts as false in a condition.
- A template only reads the context. It cannot call anything, reach a name that starts with ``_``,
  or evaluate Python.

----

Variables and Errors
--------------------

``variables`` declares what the context must hold: a list of names, or a mapping of each name to
``{"description": ..., "default": ...}``. A variable with a ``default`` is optional. Declared
variables are checked before anything is rendered, and all the missing ones are reported together.

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.utils.exception.exceptions import TemplateContextError

   mail = Mail()
   try:
       mail.send(to="qa@example.com", template="test_report", context={"passed": 98})
   except TemplateContextError as error:
       print(error.template, error.missing)      # test_report ('project',)

   preview = mail.render("test_report", {"project": "APITestka", "passed": 98})
   print(preview.subject, preview.text, preview.html)

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Exception
     - Raised when
   * - ``TemplateNotFound``
     - No directory has the template (``name``, ``searched``)
   * - ``TemplateSyntaxError``
     - A part is not valid template syntax (``line``)
   * - ``TemplateContextError``
     - The context lacks variables the template needs (``missing``, ``template``)
   * - ``TemplateRenderError``
     - A value does not fit what the template does with it, or the output passes 5 MiB

All of them subclass ``MailThunderTemplateException``. Nothing is sent when a template fails.

The rendered subject must still be one line: a context value with a line break in the subject is
refused by the checks every outgoing message passes (:doc:`mail_api`).

----

In Action Files
---------------

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_render_template", {"template": "test_report", "context": {"project": "APITestka", "passed": 98}}],
       ["MT_mail_send", {"to": "qa@example.com", "template": "test_report",
                         "context": {"project": "APITestka", "passed": 98}}]
     ]
   }

``MT_mail_render_template`` answers with ``{"subject": ..., "text": ..., "html": ...}`` and sends nothing.
