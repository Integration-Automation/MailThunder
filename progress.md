# progress.md: MailThunder

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-12).

## Open

- **#10** [BLOCKED: two releases must ship the warning first] Flip the package gate's default to refuse packages outside the allowlist.
  - Where: set `self.allow_arbitrary_packages = False` in `PackageManager.__init__` (`je_mail_thunder/utils/package_manager/package_manager_class.py`); the warning branch is je_action_core's `_check_allowed` and stays for the other projects.
  - Docs: the "Package gate" paragraph in the three READMEs and the "Package Gate" section of `docs/source/docs/{Eng,Zh}/package_manager.rst`.
  - Timing: the warning is first released in the version after 0.0.29 (`origin/main` `pyproject.toml`); flip once two releases after that one have shipped it.
  - Decide first: how a user who only runs action files (`python -m je_mail_thunder -e`, the socket server) allows a package without a Python host to call `executor.allow_packages(...)`.

## MailThunder 2.0 roadmap

From `docs/MAILTHUNDER-2.0-ROADMAP.md` (PR #45), in its priority order. One item is one focused change. P0 is done except for #24: the attachment policy (`docs/updates` U-20261008-01), the authentication abstraction (U-20261008-02), the core mail API with its provider interface (U-20261008-03) and the PyPI metadata (U-20261008-04).

- **#14** [P1] Template engine (`je_mail_thunder/templates/`: `engine.py`, `template.py`, `loader.py`).
  - What: subject / text / HTML templates with variables and metadata; shared and project-local template directories; context validation; structured rendering errors; `Mail.send(template="name", context={...})`.
  - Decide first: the roadmap prefers Jinja2-style syntax, and the package uses only the standard library (CLAUDE.md › Dependency Security). Either a small `{{ name }}` renderer in the standard library, or Jinja2 as an optional extra.
- **#15** [P1] `MicrosoftGraphProvider` (`je_mail_thunder/providers/microsoft_graph.py`).
  - What: send, drafts, message retrieval and attachments over Microsoft Graph with an OAuth2 bearer token; Graph errors mapped to MailThunder exceptions.
  - How: one class that is a `MailSender` and a `MailStore`, registered with `register_provider`; `OAuth2Auth.authorization()` is the bearer header; HTTP with `urllib`, as `utils/oauth2/oauth2.py` does.
  - Needs: the Graph scopes (`Mail.Send`, `Mail.ReadWrite`) beside the SMTP / IMAP ones in `OAUTH2_PROVIDERS`.
  - Decide first: whether the provider name `microsoft` moves from SMTP / IMAP to Graph, or Graph gets its own name.
- **#16** [P1] Mail events and triggers (`core/events.py`, `triggers/`: `trigger.py`, `filter.py`, `dispatcher.py`).
  - What: `Mail.on(event, filter, handler)`; the events `message_received`, `message_sent`, `message_failed`, `attachment_received`, `attachment_rejected`, `authentication_failed`, `connection_failed`; filters on sender, recipient, subject, body, attachments, attachment type, time and metadata; a dispatcher; the `MailTriggerBackend` interface.
  - Where the events come from: `Mail.send` and the providers already raise one exception per failure kind (`MailThunderSendException`, `MailThunderAuthenticationException`, `MailThunderConnectionException`, the attachment exceptions).
- **#17** [P2] Trigger backends: `IMAPPollingBackend`, `IMAPIdleBackend`, `GraphPollingBackend`, `GraphWebhookBackend`. Needs #16; the Graph ones need #15.
- **#18** [P2] Project Mail Layer.
  - What: a `mail/` package per automation project (`config.py`, `triggers.py`, `templates/`), scaffolded by `create_project_dir`. Needs #14 and #16.
  - Cross-repo: using it from APITestka, WebRunner and LoadDensity belongs in `D:\Codes\progress.md`.
- **#19** [P3] [DECIDE] MailThunder Studio: a UI over the core API (Dashboard, Accounts, Templates, Triggers, Policies, Projects, Logs, Settings).
  - Decide first: the UI toolkit, and whether it ships in this package or in its own.
- **#20** [P4] Webhook / event extensions, provider health monitoring, audit logging, further providers.
- **#24** [UNVERIFIED] The core mail API has not been run against a real mailbox.
  - Tested so far: fake SMTP / IMAP clients, and a fake SMTP server on localhost for what reaches the wire (`test/unit_test/test_mail_providers.py`).
  - To check on Gmail and Microsoft 365: `send` with attachments and both bodies; `get_messages` (newest first, `unread_only`, a non-ASCII `query`, which is sent as UTF-8 in a quoted string with `CHARSET UTF-8`); `create_draft` finding the folder flagged `\Drafts`; `delete_message` with `UID EXPUNGE`; a non-ASCII folder name; a connection left idle past the server's timeout.
  - Where: a script under `test/unit_test/manual_test/`, which the test run does not collect.
- **#22** [DECIDE] The roadmap's examples import `mailthunder`; the package is `je_mail_thunder`, which PyBreeze imports (`architecture.md` §6). Keep the name, or also ship a `mailthunder` import name (check first that the name is free on PyPI).
