Mail Events and Triggers
========================

``Mail`` reports what happens to mail as events, in the same words whatever the provider is,
and a trigger backend watches a folder so that new mail becomes an event too.

.. code-block:: python

   from je_mail_thunder import Mail

   mail = Mail()

   def handle_report(event):
       print("new report from", event.message.sender, event.message.subject)

   mail.on("message_received", handle_report, filter={"subject": "[TEST]", "has_attachments": True})
   mail.watch("INBOX")          # look every 60 seconds on a background thread
   ...
   mail.close()                 # stops the watching and closes the connections

----

Events
------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Event
     - When
   * - ``message_received``
     - A watched folder has a new message
   * - ``attachment_received``
     - Once for each attachment of a new message
   * - ``message_sent``
     - ``send`` handed a message to the provider
   * - ``message_failed``
     - ``send`` or ``create_draft`` failed, whatever the reason
   * - ``attachment_rejected``
     - An attachment was missing or broke the attachment policy
   * - ``authentication_failed``
     - There were no credentials, or the server refused the login
   * - ``connection_failed``
     - The server could not be reached, or the connection was lost

A failure is still raised to the caller; the events are how other code hears about it. A failed
send emits its reason first and ``message_failed`` after it. ``"*"`` subscribes to every event.

A handler receives a ``MailEvent``:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Attribute
     - Content
   * - ``name``
     - The event's name
   * - ``message``
     - The ``MailMessage`` it is about, when there is one
   * - ``attachment``
     - The ``Attachment`` of an ``attachment_received`` event
   * - ``error``
     - The exception behind a failure
   * - ``provider``, ``folder``
     - The provider's name and, for received mail, the folder
   * - ``timestamp``, ``metadata``
     - When it happened (UTC), and anything else the source knows
   * - ``to_dict()``
     - The event as JSON-ready values

A handler that raises is logged and stops neither the other handlers nor the operation.

----

Subscribing
-----------

.. code-block:: python

   subscription = mail.on("message_failed", notify_team)
   mail.events.off(subscription)

   @mail.on("attachment_received", filter={"attachment_type": "pdf"})
   def save_report(event):
       event.attachment.save("reports")

``filter`` is a mapping of rules, a function of the event, or a ``MailFilter``. An event passes
when every rule matches:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Rule
     - Matches when
   * - ``sender``
     - The text is in the sender's address
   * - ``recipient``
     - The text is in one of the ``to`` / ``cc`` / ``bcc`` addresses
   * - ``subject``, ``body``
     - The text is in the subject, or in the text or HTML body
   * - ``has_attachments``
     - The message has attachments (``True``) or none (``False``)
   * - ``attachment_type``
     - One attachment has the extension (``"pdf"``) or the MIME type (``"image/*"``)
   * - ``since``, ``until``
     - The message's date is inside the range
   * - ``metadata``
     - The event's metadata holds these values
   * - ``predicate``
     - The function returns true for the event

Text rules ignore case and look anywhere in the field; a compiled regular expression is applied
with ``search``.

----

Watching a Folder
-----------------

.. code-block:: python

   mail.watch("INBOX", interval=30)            # ask every 30 seconds
   mail.watch("INBOX", idle=True)              # IMAP IDLE: the server says when mail arrives
   backend = mail.watch("Reports", start=False)
   mail.triggers.poll()                        # look once, e.g. from a scheduled job

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Meaning
   * - ``folder``
     - The folder to watch (``"INBOX"``)
   * - ``idle``
     - Wait for the server instead of asking at intervals. Needs a provider that can (IMAP)
   * - ``start``
     - Watch on a daemon thread from now on (``True``), or only when ``mail.triggers.poll()`` is called
   * - ``interval``
     - Seconds between two looks (60); with ``idle``, the longest one IDLE lasts (300)
   * - ``include_existing``
     - Also report the mail that is already there. By default the first look only notes it
   * - ``batch_limit``
     - Messages read per look (50). More than that arriving between two looks are missed

The watcher uses a connection of its own, so it does not get in the way of ``send`` or
``get_messages``. A look that fails is logged, reported as ``authentication_failed`` or
``connection_failed`` when it is one, and tried again 30 seconds later.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Backend
     - How it notices new mail
   * - ``PollingBackend``
     - Asks any ``MailStore`` for its newest messages and reports the ones it has not seen
   * - ``IMAPPollingBackend``
     - The same, but after the first look searches only ``UID <last + 1>:*``
   * - ``IMAPIdleBackend``
     - Waits in IMAP ``IDLE`` (RFC 2177) between looks; falls back to sleeping when the server has no ``IDLE``

``mail.triggers`` holds the backends (``backends``, ``add``, ``remove``, ``poll``, ``start``, ``stop``).
A backend of your own subclasses ``MailTriggerBackend`` and implements ``poll()``;
``register_backends(store_class, polling, push)`` in ``je_mail_thunder.triggers.factory`` tells
``Mail.watch`` which backend watches a kind of provider.

----

In Action Files
---------------

An action file cannot register a handler, but it can ask what arrived:

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_poll", {"folder": "INBOX"}]
     ]
   }

The first ``MT_mail_poll`` of a folder notes what is there and answers with an empty list; each later
one answers with the ``message_received`` and ``attachment_received`` events since the one before.
