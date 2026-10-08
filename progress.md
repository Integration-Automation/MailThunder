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

From `docs/MAILTHUNDER-2.0-ROADMAP.md` (PR #45), in its priority order. One item is one focused change. Every tier of the roadmap is implemented (`docs/updates` U-20261008-05 to U-20261008-14 for P1 to P4); what follows is what is left. P0: the attachment policy (`docs/updates` U-20261008-01), the authentication abstraction (U-20261008-02), the core mail API with its provider interface (U-20261008-03) and the PyPI metadata (U-20261008-04).

- **#18** [P2] [BLOCKED: the other repositories] Use the project mail layer from APITestka, WebRunner and LoadDensity.
  - Here it is done (`docs/updates` U-20261008-10): `project_mail()`, the `mail/` layout, and `create_project_dir` scaffolding it.
  - There: each project gets a `mail/` directory and sends its reports with `project_mail().send(template=...)`. That is a workspace item for `D:\Codes\progress.md`; `architecture.md` §6 names the contract.
- **#26** MailThunder Studio follow-ups (`docs/updates` U-20261008-12 has what exists).
  - Nothing is saved: a policy changed on the Policies page lasts until Studio stops, and accounts, templates and triggers are shown, not edited. Editing would mean writing `mail/config.py`, template files or `mail_thunder_content.json` from the page.
  - The page has only been checked by parsing its script (esprima) and by driving the API over HTTP; nobody has looked at it in a browser yet. Check the eight pages, both languages and the dark colour scheme.
- **#25** Microsoft Graph reaches only the signed-in user's mailbox (`/me`, a delegated token). A shared mailbox or an app-only token (client credentials, `/users/{id}`) needs a mailbox setting on `MailAccount` and a client-credentials grant in `utils/oauth2/oauth2.py`.
- **#24** [UNVERIFIED] The core mail API has not been run against a real mailbox.
  - Tested so far: fake SMTP / IMAP clients, and a fake SMTP server on localhost for what reaches the wire (`test/unit_test/test_mail_providers.py`).
  - To check on Gmail and Microsoft 365: `send` with attachments and both bodies; `get_messages` (newest first, `unread_only`, a non-ASCII `query`, which is sent as UTF-8 in a quoted string with `CHARSET UTF-8`); `create_draft` finding the folder flagged `\Drafts`; `delete_message` with `UID EXPUNGE`; a non-ASCII folder name; a connection left idle past the server's timeout; `mail.watch()` and `mail.watch(idle=True)` (`IMAPProvider.idle` writes `IDLE` / `DONE` itself and has only been run against a scripted client).
  - To check on Microsoft Graph (`provider="microsoft_graph"`): the token asked for with the Graph scopes; `send` inline and through a draft with an upload session (an attachment over 3 MiB); `get_messages` with `unread_only` and a `query` (the filter starts with `receivedDateTime` so Graph accepts the ordering); a folder by display name; `GraphWebhookBackend` behind a public HTTPS address (validation, a notification, renewal, removal).
  - How: `python test/unit_test/manual_test/mail/mail_api_manual_test.py [provider]` from a directory with `mail_thunder_content.json`. It mails the account itself, reads the inbox, stores and deletes a draft and looks twice for new mail. It has only been run against the `file` provider.
  - Not covered by the script: IMAP IDLE (`mail.watch(idle=True)`), the Graph upload session, and `GraphWebhookBackend`.
