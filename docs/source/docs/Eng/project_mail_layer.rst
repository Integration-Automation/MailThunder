Project Mail Layer
==================

An automation project keeps how it mails in its own ``mail/`` directory, and its code asks for a
ready ``Mail`` without naming a provider. Moving the project to another provider, or trying it
without sending anything, is then a change in one file.

.. code-block:: text

   MyProject/
     api/
     reports/
     mail/
       config.py       # provider, login, attachment policy, audit log
       triggers.py     # what the project does when mail arrives or fails
       templates/      # the project's mail templates
         test_report/
           subject.txt
           body.txt
           body.html
           template.json

.. code-block:: python

   from je_mail_thunder import project_mail

   mail = project_mail()                    # the project in the working directory
   mail.send(to="qa@example.com", template="test_report",
             context={"project": "MyProject", "passed": 98, "failed": 2,
                      "failures": [{"name": "login", "reason": "timeout"}]})
   mail.triggers.poll()                     # look once for new mail
   mail.close()

``create_project_dir()`` scaffolds the layer together with the ``keyword/`` and ``executor/``
directories (:doc:`project_templates`). The scaffolded ``config.py`` uses the ``file`` provider, so
a new project keeps its mail on disk until a real provider is named.

----

config.py
---------

Every name is optional. Without ``config.py`` the project gets the same ``Mail()`` as any other code.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Name
     - Meaning
   * - ``PROVIDER``
     - A registered provider name: ``"google"``, ``"microsoft"``, ``"microsoft_graph"``, ``"yahoo"``,
       ``"icloud"``, ``"zoho"``, ``"fastmail"``, ``"smtp"`` or ``"file"``
   * - ``AUTH``
     - An authentication object. Without it the login comes from ``mail_thunder_content.json`` or the
       environment, which keeps credentials out of the project's files
   * - ``ACCOUNT``
     - A whole ``MailAccount`` (for ``"smtp"`` with its ``MailServers``), instead of ``PROVIDER`` and ``AUTH``
   * - ``ATTACHMENT_POLICY``
     - The ``AttachmentPolicy`` every message of the project is checked against
   * - ``AUDIT``
     - ``True`` records every mail event in ``mail/audit.jsonl``; a path records there; ``False`` records nothing

.. code-block:: python

   from je_mail_thunder import AttachmentPolicy

   PROVIDER = "microsoft_graph"
   ATTACHMENT_POLICY = AttachmentPolicy(max_total_size=20 * 1024 * 1024, allowed_extensions={"html", "pdf"})
   AUDIT = True

.. warning::

   Do not put a password or a token in ``config.py`` if the project is committed to a repository.
   Leave ``AUTH`` out and let the login come from ``mail_thunder_content.json`` (git-ignored) or the
   environment.

----

triggers.py
-----------

``triggers.py`` defines ``register(mail)``, which ``project_mail`` calls once. It subscribes the
project's handlers and says which folders are watched (:doc:`mail_triggers`).

.. code-block:: python

   def register(mail):
       @mail.on("message_received", filter={"subject": "[RERUN]"})
       def rerun_requested(event):
           print("rerun requested by", event.message.sender)

       @mail.on("message_failed")
       def report_not_sent(event):
           print("report not sent:", event.error)

       mail.watch("INBOX", start=False)     # start=True watches on a background thread

----

templates/
----------

The project's templates are found before the shared ones, so a project can replace a shared template
by giving its own the same name (:doc:`mail_templates`).

----

What Is Loaded, and When
------------------------

- ``project_mail(project=None)`` runs ``mail/config.py`` and ``mail/triggers.py``. They are Python files
  of the project, run like any other module of it: load only the layer of a project whose code you trust.
  No action command loads a layer, so an action file or a socket client cannot make one run.
- ``describe_mail_layer(project=None)`` only looks at the files: which of them exist and which templates
  there are. It runs nothing.
- Nothing connects until the ``Mail`` is used, and no trigger runs unless ``triggers.py`` starts one.
- A project without a ``mail`` directory, a setting of the wrong type, a file that cannot be run or a
  ``triggers.py`` without ``register`` raises ``MailThunderProjectException`` naming the file.
