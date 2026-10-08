Monitoring: Audit Log, Provider Health and Webhooks
===================================================

Three listeners turn the mail events (:doc:`mail_triggers`) into something to look at afterwards:
an audit log, a health report per provider, and outgoing webhooks. Each one is attached to
``mail.events`` and none of them can stop a mail.

.. code-block:: python

   from je_mail_thunder import AuditLog, Mail, ProviderHealth, WebhookForwarder

   mail = Mail()
   audit = AuditLog()
   health = ProviderHealth()
   audit.attach(mail.events)
   health.attach(mail.events)
   mail.on("*", WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret"))

----

Audit Log
---------

``AuditLog`` appends one JSON object per event to a file: who sent or received what, and when.

.. code-block:: json

   {"timestamp": "2026-10-08T09:30:00+00:00", "event": "message_sent", "provider": "smtp", "folder": "",
    "message_id": null, "internet_message_id": null, "sender": "ci@example.com", "to": ["qa@example.com"],
    "cc": [], "bcc": [], "attachments": [{"filename": "q3.pdf", "content_type": "application/pdf", "size": 48213}],
    "subject": "Q3 report"}

- It records addresses, the subject, attachment names and sizes, the provider and, for a failure, the
  error's type and message. It never records a body, the content of an attachment or a credential.
- ``AuditLog(subjects=False)`` leaves the subject lines out.
- The file is ``~/.je_mail_thunder/audit/mail_audit.jsonl`` unless ``MAIL_THUNDER_AUDIT_FILE`` or
  ``AuditLog(path)`` names another. It is only appended to, and moved to ``<name>.1`` past 10 MiB.
- ``audit.entries(limit=100)`` returns the newest entries.
- A file that cannot be written is logged and the mail goes on.

----

Provider Health
---------------

``ProviderHealth`` counts what each provider did and how it ended.

.. code-block:: python

   for status in health.report():
       print(status["provider"], status["state"], status["last_error"])

   health.probe(mail.providers)        # ask each provider to connect and log in, now

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - State
     - Meaning
   * - ``unknown``
     - Nothing happened on the provider yet
   * - ``healthy``
     - The last thing it did succeeded
   * - ``degraded``
     - It failed, fewer than ``failure_threshold`` times in a row (3 by default)
   * - ``down``
     - It failed ``failure_threshold`` times in a row

A status also carries ``successes``, ``failures``, ``consecutive_failures``, ``last_success``,
``last_failure`` and ``last_error``. Only the provider's own failures count: a refused login, a lost
connection, a message the server refused. A missing recipient or a refused attachment is the caller's
mistake and changes nothing.

``probe`` calls each provider's ``check()``, which connects and logs in without sending or reading
mail, and records the outcome.

----

Webhooks
--------

``WebhookForwarder`` is an event handler that posts each event to an HTTPS address as JSON.

.. code-block:: python

   forwarder = WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret")
   mail.on("message_failed", forwarder)
   mail.on("message_received", forwarder, filter={"subject": "[ALERT]"})
   ...
   forwarder.close()                   # posts what is still queued

- Events are queued and posted in order by one background thread, so a slow receiver never delays
  ``send``. When 1000 events wait (``queue_size``), new ones are dropped and logged.
- The payload is the event's ``to_dict()`` without the message bodies; ``bodies=True`` includes them.
  Attachments are described, never included.
- With a ``secret``, each request carries ``X-MailThunder-Signature: sha256=<HMAC-SHA256 of the body>``.
  The receiver computes the same value over the raw body and compares; ``X-MailThunder-Event`` names
  the event.
- Only ``https`` addresses are accepted. A receiver that answers with an error status is logged.

Checking the signature on the receiving side:

.. code-block:: python

   import hashlib
   import hmac

   def is_from_mail_thunder(secret: str, body: bytes, signature_header: str) -> bool:
       expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
       return hmac.compare_digest(expected, signature_header)
