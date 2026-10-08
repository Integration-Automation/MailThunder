# MailThunder Architecture

> Short overview for people and agents.
> Last verified: 2026-10-08 against `cb23fb1` on `feat/mailthunder-2.0`.

## 1. Purpose

MailThunder (`je_mail_thunder`, PyPI `je-mail-thunder`) is a small email automation library that
uses only the standard library and `je_action_core`. `pyproject.toml` builds `je_mail_thunder` and `dev.toml` builds
`je_mail_thunder_dev`. `SMTPWrapper` and `IMAPWrapper` extend `smtplib.SMTP_SSL` and
`imaplib.IMAP4_SSL` (and `SMTPStartTLSWrapper` extends `smtplib.SMTP`, upgraded with STARTTLS) with credential
lookup, password or OAuth2 (`XOAUTH2`) login, logging and context-manager support. A JSON action
executor exposes the same operations to action files, a CLI and a TCP socket server.
The core mail API (`Mail`) puts a provider interface over those wrappers, so callers send and read mail
without naming a protocol; it is the foundation of the MailThunder 2.0 roadmap
(`docs/MAILTHUNDER-2.0-ROADMAP.md`; what is left of it: `progress.md`).

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `je_mail_thunder/__init__.py` | Public facade (`__all__`) |
| `je_mail_thunder/__main__.py` | Legacy flag CLI (`python -m je_mail_thunder`) |
| `je_mail_thunder/smtp/smtp_wrapper.py` | `SMTPClientMixin` (messages, login, send, quit; `attachment_policy` checked before a send with an attachment; mixed in before an `smtplib` class), `SMTPWrapper(SMTPClientMixin, SMTP_SSL)` (default `smtp.gmail.com:465`), `SMTPStartTLSWrapper(SMTPClientMixin, SMTP)` (default `smtp.office365.com:587`; STARTTLS before anything else, refused when the server lacks it), `default_smtp_client()` and the module instance `smtp_instance` (a `LazyInstance` of it) |
| `je_mail_thunder/imap/imap_wrapper.py` | `IMAPWrapper(IMAP4_SSL)` (default `imap.gmail.com`; `oauth2_login`), `default_imap_client()` and the module instance `imap_instance` (a `LazyInstance` of it) |
| `je_mail_thunder/core/` | The provider-agnostic API: `mail.Mail` (send, create_draft, get_messages, get_message, delete_message, close; checks a message and its attachments, then hands it to a provider; one lock per instance) and the module instance `mail_instance`; `message.MailMessage` (frozen; `check_outgoing` refuses what cannot be sent); `rfc822` (to and from `email.message.EmailMessage`); `account.MailAccount` / `MailServers` / `default_account()`; `events` (`MailEvent`, the seven event names, `failure_events`); `actions` (the `MT_mail_*` commands, JSON-ready); `compat` (`legacy_message`, `mail_from_wrappers`); `project` (`project_mail`: the `Mail` a project's `mail/config.py`, `mail/triggers.py` and `mail/templates/` describe; `describe_mail_layer` reads the files without running them) |
| `je_mail_thunder/providers/` | Backends behind `Mail`: `base.MailProvider` with the roles `MailSender` and `MailStore`, and `check()` (connect and log in, nothing else); `session.WrapperProvider` (a wrapper connection opened and logged in on first use, pinged after 30 idle seconds, replaced when dead; an already connected wrapper is used as it is); `smtp.SMTPProvider`; `imap.IMAPProvider` (UIDs, `BODY.PEEK[]`, `\Drafts` lookup, modified UTF-7 folder names, `idle`); `microsoft_graph.MicrosoftGraphProvider` (sender and store over `https://graph.microsoft.com/v1.0` with an OAuth2 bearer token; `http.https_request` is its client, https only); `file.FileProvider` (`.eml` files under `$MAIL_THUNDER_FILE_PROVIDER_DIR` or `./mail_outbox`, for dry runs); `registry` (`register_provider`, `create_providers`; `google`, `microsoft`, `yahoo`, `icloud`, `zoho`, `fastmail`, `smtp`, `microsoft_graph`, `file`) |
| `je_mail_thunder/templates/` | Mail templates: `engine` (a Jinja2-style subset in the standard library: `{{ }}` with filters, `{% if %}`, `{% for %}`; reads the context only, HTML-escapes on request, output capped at 5 MiB), `template.MailTemplate` (subject / text / HTML, declared variables with defaults, metadata; `render` → `RenderedTemplate`), `loader.TemplateLoader` (`<name>.json` or `<name>/` in `./mail/templates`, then `$MAIL_THUNDER_TEMPLATE_DIR` or `~/.je_mail_thunder/templates`; names are never paths) |
| `je_mail_thunder/triggers/` | Mail events: `filter.MailFilter` (sender, recipient, subject, body, attachments, time, metadata, predicate), `dispatcher.EventDispatcher` (`on` / `off` / `emit`; a handler that raises is logged, never propagated), `trigger.MailTriggerBackend` (`poll`, and `start` / `stop` on a daemon thread that survives failures) and `TriggerManager`, `polling.PollingBackend` (any `MailStore`; first look is the baseline), `imap.IMAPPollingBackend` (`UID n:*`) / `IMAPIdleBackend` (RFC 2177), `graph.GraphPollingBackend` (`receivedDateTime ge`) / `GraphWebhookBackend` (subscription plus a localhost listener for change notifications, checked by `clientState`), `webhook.WebhookForwarder` (an event handler that posts events to an https address from a queue, signed with HMAC-SHA256), `factory` (which backend watches which store) |
| `je_mail_thunder/monitoring/` | Listeners of the mail events: `audit.AuditLog` (one JSON line per event in `$MAIL_THUNDER_AUDIT_FILE` or `~/.je_mail_thunder/audit/mail_audit.jsonl`; facts only, never a body, attachment content or credential; append-only, rotated at 10 MiB) and `health.ProviderHealth` (unknown / healthy / degraded / down per provider from the events, and `probe` through `MailProvider.check()`) |
| `je_mail_thunder/studio/` | MailThunder Studio, a local web page over the core API only: `api.StudioApi` (JSON-ready methods for the eight pages: dashboard, accounts, templates, triggers, policies, projects, logs, settings; never returns a secret), `server.StudioServer` / `start_studio` (standard-library HTTP server on `localhost:9947`; token and `Host` checked on every request), `page` (the HTML, CSS and script as text), `__main__` (`python -m je_mail_thunder.studio`) |
| `je_mail_thunder/auth/` | How an account logs in, behind one interface: `base.Authentication` (`user`, `mechanism`, `login(client)` for the SMTP / IMAP wrappers, `authorization()` for HTTP; what a mechanism cannot do raises `MailThunderAuthenticationException`), `password.PasswordAuth` / `AppPasswordAuth`, `oauth2.OAuth2Auth` (bearer token from `utils/oauth2`'s cache), `xoauth2.XOAUTH2Auth` (the same token as SASL `XOAUTH2`); secrets stay out of every `repr` |
| `je_mail_thunder/attachments/` | What a message may carry: `attachment.Attachment` (a file to send by `path`, or one that arrived as `content`; `save` writes it under `mime.safe_filename`), `policy.AttachmentPolicy` / `DEFAULT_ATTACHMENT_POLICY` (count, size, extension and MIME-type limits), `validator.validate_attachments` (count → existence → size → extension → MIME type → total size; raises the `MailThunderAttachmentException` subclasses), `mime` (type and extension from the file name) |
| `je_mail_thunder/utils/oauth2/oauth2.py` | OAuth2 with the standard library: `OAUTH2_PROVIDERS` (`google`, `microsoft`: token URL, scope, SMTP/IMAP hosts), `OAuth2Settings` (secrets out of `repr`), `refresh_access_token` (https only), `OAuth2TokenCache` / `oauth2_token_cache`, `xoauth2_string` |
| `je_mail_thunder/utils/executor/action_executor.py` | `Executor` (je_action_core's `ActionExecutor` with MailThunder's settings): `event_dict` (`MT_*` commands plus je_action_core's `SAFE_BUILTINS` allowlist), `execute_action`, `execute_files`, `add_command_to_executor`, `action_list_from_mapping` |
| `je_mail_thunder/utils/save_mail_user_content/` | Credential sources: `mail_thunder_content.json` in the working directory (`read_output_content` / `write_output_content`) and the env vars `mail_thunder_user` / `mail_thunder_user_password` (`set_/get_mail_thunder_os_environ`); `credentials.resolve_login_credentials` picks one, for both wrappers; `credentials.resolve_oauth2_settings` reads the `"oauth2"` object of the file, else the `mail_thunder_oauth2_*` env vars, and `configured_oauth2_provider` picks the servers the module instances connect to; `credentials.resolve_authentication` returns the same choice as an `auth` object (`XOAUTH2Auth`, else `PasswordAuth`, else `None`); `credentials.configured_mail_provider` reads `"mail_provider"` / `mail_thunder_mail_provider`, the provider of `Mail()` |
| `je_mail_thunder/utils/socket_server/mail_thunder_socket_server.py` | `start_mail_thunder_socket_server`: je_action_core's TCP action server (old name `start_autocontrol_socket_server` kept as a deprecated alias) with payload validation first (`_validate_payload`, `MAX_ACTIONS`) and oversized payloads dropped |
| `je_mail_thunder/utils/package_manager/` | `package_manager` (je_action_core's, gate on): loads an installed package's members into the executor; `executor.allow_packages` / `set_allow_arbitrary_packages` are its Python-only switches |
| `je_mail_thunder/utils/project/` | `create_project_dir` scaffolding (`keyword/`, `executor/` and the project mail layer `mail/`); `template/template_keyword.py`, `template_executor.py` and `template_mail.py` hold the templates |
| `je_mail_thunder/utils/{json,json_format,file_process,logging,exception}/` | Action JSON I/O (je_action_core's `ActionJsonFile`), JSON reformat, directory listing (je_action_core's), `mail_thunder_logger` (file at `$MAIL_THUNDER_LOG_FILE` or `~/.je_mail_thunder/logs/Mail_Thunder.log`, opened on first use), `MailThunderException` hierarchy |
| `scripts/dev_release.py` | Release helper for the dev channel, run only by CI (standard library only): `prepare` writes `pyproject.toml` from `dev.toml` with the next version, `changed <dist>` compares the built wheel with the newest published one |
| `test/unit_test/` | pytest suite (`testpaths = ["test"]`). `manual_test/` holds scripts that need real mailboxes; its `conftest.py` excludes them from collection |
| `docs/source/` | Sphinx docs (`docs/Eng`, `docs/Zh`, `docs/API`) |

## 3. Entry points and public interfaces

- **Python facade**: `import je_mail_thunder` gives you:
  - wrappers: `SMTPWrapper`, `smtp_instance`, `IMAPWrapper`, `imap_instance`;
  - core mail API: `Mail`, `mail_instance`, `MailMessage`, `MailAccount`, `MailServers`, `MailProvider`, `MailSender`, `MailStore`,
    `SMTPProvider`, `IMAPProvider`, `MicrosoftGraphProvider`, `GraphPollingBackend`, `GraphWebhookBackend`, `register_provider`, `registered_providers`, `legacy_message`, `mail_from_wrappers`;
  - attachments: `Attachment`, `AttachmentPolicy`, `DEFAULT_ATTACHMENT_POLICY`, `validate_attachments`;
  - templates: `MailTemplate`, `RenderedTemplate`, `TemplateLoader`, `render_string`;
  - events and triggers: `MailEvent`, `EVENT_NAMES`, `MailFilter`, `EventDispatcher`, `MailTriggerBackend`, `PollingBackend`,
    `IMAPPollingBackend`, `IMAPIdleBackend`;
  - monitoring: `AuditLog`, `ProviderHealth`, `WebhookForwarder`; `FileProvider`;
  - project mail layer: `project_mail`, `describe_mail_layer`;
  - authentication: `Authentication`, `PasswordAuth`, `AppPasswordAuth`, `OAuth2Auth`, `XOAUTH2Auth`, `resolve_authentication`;
  - execution: `execute_action`, `execute_files`, `add_command_to_executor`, `read_action_json`,
    `get_dir_files_as_list`, `create_project_dir`;
  - credentials: `read_output_content`, `write_output_content`, `set_mail_thunder_os_environ`,
    `get_mail_thunder_os_environ`, `mail_thunder_content_data_dict`, `is_need_to_save_content`.
- **Action format**: an action is `[name]`, `[name, {kwargs}]` or `[name, [args]]`. A file holds a
  list of actions or `{"mail_thunder": [...]}`. The old key `auto_control`, copied from AutoControl, is
  still read with a `DeprecationWarning` (`action_list_from_mapping` in `utils/executor/action_executor.py`).
- **Commands**: examples are `MT_smtp_later_init`, `MT_smtp_create_message_and_send`,
  `MT_imap_select_mailbox`, `MT_imap_output_all_mail_as_file` and `MT_add_package_to_executor`.
  `MT_smtp_quit` closes the SMTP connection; its pre-prefix name `smtp_quit` is still registered.
  `MT_mail_send`, `MT_mail_create_draft`, `MT_mail_get_messages`, `MT_mail_get_message`, `MT_mail_delete_message` and
  `MT_mail_close` are the core mail API on `mail_instance`, with JSON-ready arguments and results (`core/actions.py`);
  `MT_mail_render_template` previews a template and `MT_mail_poll` answers with the events of the mail that arrived since the last poll.
- **CLI**: `python -m je_mail_thunder` takes:
  - `-e/--execute_file <json>`, `-d/--execute_dir <dir>`, `-c/--create_project <path>` and `--execute_str <json>`;
  - on `win32`/`cygwin`/`msys`, `--execute_str` is decoded with `json.loads` twice;
  - any error prints `repr(error)` to stderr and exits with code 1.

  No console script is declared.
- **TCP socket server**: `je_mail_thunder.utils.socket_server.mail_thunder_socket_server.start_mail_thunder_socket_server(host="localhost", port=9942)` (the old name `start_autocontrol_socket_server` still works with a `DeprecationWarning`).
  - The facade does not re-export it.
  - If `sys.argv` carries one or two extra arguments, they override the host and port.
  - `quit_server` shuts it down.
  - Replies end with `Return_Data_Over_JE`.
- **PyPI packages**: `je_mail_thunder` (stable) and `je_mail_thunder_dev` (dev channel), both published by CI.
  - Stable: a push to `main` runs `publish_stable.yml`, which bumps `pyproject.toml`, uploads, tags and
    creates the GitHub release.
  - Dev: the `publish-dev` job of `test_dev.yml` runs after the `test` matrix on a push to `dev`, builds from
    `dev.toml` and uploads when the commit is still the tip of `dev` and the wheel differs from the newest
    published one. `scripts/dev_release.py` takes the version from PyPI (newest release plus one patch), so
    nothing is committed back and the version in `dev.toml` is only a floor. The job reads no secret but
    `PYPI_API_TOKEN`.
  - Both jobs install only the hash-locked `.github/requirements/publish.txt` and build with
    `python -m build --no-isolation`, so the build backend is the locked `setuptools` too.
  - `test/unit_test/test_dev_toml_parity.py` keeps the dependencies, Python floor, entry points and
    `[tool.setuptools]` of `dev.toml` equal to `pyproject.toml`.
- **MailThunder Studio**: `python -m je_mail_thunder.studio [--host HOST] [--port PORT] [--project DIR] [--no-browser]`, or
  `je_mail_thunder.studio.server.start_studio(mail=None, host="localhost", port=9947, project=None)`.
  - It serves one page, `/studio.js`, `/studio.css` and a JSON API under `/api/`; the facade does not re-export it.
  - Every `/api/` request needs the header `X-MailThunder-Token` with the token of that run, and every request a `Host` of the
    address it was started on.
- There is no MCP server, LSP or pytest plugin, and no desktop GUI: Studio is a page in the browser.

## 4. Main flows

**Action → mail server**

```
action JSON / --execute_str → __main__ → execute_action → Executor._execute_event
  → event_dict["MT_*"] → deferred call on smtp_instance / imap_instance (connects on first use) → smtplib / imaplib over SSL
  → record dict {"execute: <action>": return value | repr(error)} → mail_thunder_logger
```

**Login**

```
MT_smtp_later_init / MT_imap_later_init → try_to_login_with_env_or_content
  → resolve_oauth2_settings() → oauth2_token_cache.access_token() (refresh at the token endpoint) → oauth2_login (AUTH XOAUTH2)
  → else _resolve_credentials (credentials.resolve_login_credentials)
  → read_output_content() (./mail_thunder_content.json) else get_mail_thunder_os_environ() → login()
```

**Core mail API**

```
Mail.send(**fields) / MT_mail_send → template + context rendered into subject / text / html (TemplateLoader) → message_from_fields → sender defaults to account.authentication().user
  → check_outgoing (a recipient, valid addresses, one-line subject and headers) → validate_attachments(policy)
  → the first MailSender of create_providers(account) → SMTPProvider._live_client()
       first use: account.authentication() → SMTPWrapper / SMTPStartTLSWrapper → auth.login(client)
       idle over 30 s: NOOP, and a new connection when it does not answer
  → to_email_message → client.send_message → logged and raised as a MailThunder exception on failure, never retried
Mail.get_messages(...) / MT_mail_get_messages → the first MailStore → IMAPProvider
  → EXAMINE folder → UID SEARCH → UID FETCH BODY.PEEK[], one message per step of the iterator → parse_message
```

**Events and triggers**

```
Mail.send → provider.send → events.emit(message_sent)
          ↘ on a MailThunder exception: failure_events → attachment_rejected / authentication_failed /
            connection_failed, then message_failed → the exception is raised to the caller
Mail.watch(folder) → create_backend(a store with its own connection) → triggers.add → daemon thread:
  poll (first look = baseline) → message_received + attachment_received per new message → EventDispatcher.emit
  → subscriptions whose MailFilter matches → handler(event); wait(interval) or IMAP IDLE; a failed look retries in 30 s
```

**Socket**: TCP client → `TCPServerHandler.handle` (8192-byte cap, `_validate_payload`) →
`execute_action` → return values, then `Return_Data_Over_JE`.

**Import-time behaviour**: importing opens no connection. `smtp_instance` and `imap_instance` are
`LazyInstance` proxies (`utils/lazy_instance/lazy_instance.py`) that build the real client
(`default_smtp_client()` / `default_imap_client()`: the OAuth2 provider's servers when the settings name one,
else Gmail) — and so connect — the first time anything is read from them; a connection failure
raises there, at use, and the next use retries. `Executor.__init__` registers `deferred(instance,
"method")` callables, which look the method up only when the action runs, so building the executor
does not connect either. Login still waits until `later_init`.
`mail_instance = Mail()` reads and connects nothing either: its account and providers are worked out on the first call.

## 5. Extension points

- **New command**, in this order:
  1. Add a method on the wrapper, or a function in a `utils/` module. Log through `mail_thunder_logger`
     and write `:param` / `:return:` docstrings.
  2. Register it in `Executor.__init__` (`utils/executor/action_executor.py`) with an `MT_` prefix.
  3. If it is public, export it from `je_mail_thunder/__init__.py` and `__all__`.
  4. Add a test in `test/unit_test/` (for example `test_executor.py`).

  At runtime, use `add_command_to_executor({...})` (functions and methods only) or
  `MT_add_package_to_executor`.
- **New protocol wrapper**:
  1. Create a subpackage such as `je_mail_thunder/<proto>/<proto>_wrapper.py` that subclasses the
     stdlib client.
  2. Give it `__enter__` / `__exit__` and `later_init`, and reuse the credential flow in
     `save_mail_user_content/`.
  3. Add a module-level instance, register it in the executor, export it from the facade, and add tests.
- **New mail provider**:
  1. Implement `providers.base.MailSender` and / or `MailStore`. A provider over one of the wrappers subclasses
     `providers.session.WrapperProvider`, which gives it the lazy, logged-in, idle-checked connection.
  2. Raise `MailThunderProviderException` subclasses for server errors; never retry a send.
  3. Register it with `providers.registry.register_provider(name, factory)`; `Mail` is not edited.
  4. Test it against a fake client (`test/unit_test/mail_fakes.py`).
- **New trigger backend**: subclass `triggers.trigger.MailTriggerBackend` (`poll()` emits `MailEvent`s through `self._emit`),
  or `triggers.polling.PollingBackend` when the provider is a `MailStore`, and name it for its store with
  `triggers.factory.register_backends`.
- **New credential source**: extend `save_mail_user_content/` and `credentials.resolve_login_credentials`, which
  both wrappers use, and `credentials.resolve_authentication`.
- **New login mechanism**: subclass `auth.base.Authentication` (set `mechanism`, override `login` and / or
  `authorization`), keep its secret out of `repr`, and export it from the facade.
- **Project template keyword**: edit `utils/project/template/template_keyword.py` /
  `template_executor.py`, which are wired from `utils/project/create_project_structure.py`.
- **Project mail layer setting**: add the name and its type to `_SETTINGS` in `core/project.py`, use it in `project_mail`,
  and show it in the scaffolded `mail_config_template` (`utils/project/template/template_mail.py`).

## 6. Cross-project boundaries

- **Automation projects (APITestka, WebRunner, LoadDensity)** are meant to mail through the project mail layer:
  `project_mail()` and the `mail/` layout (`config.py` names, `triggers.py` `register(mail)`, `templates/`) are the
  contract. None of them uses it yet (workspace item, `D:\Codes\progress.md`).
- **PyBreeze (subprocess)**: `call_mail_thunder` (`PyBreeze/pybreeze/extend/process_executor/mail_thunder/mail_thunder_process.py`)
  → `build_process(..., "je_mail_thunder", ...)` → `python -m je_mail_thunder --execute_str/--execute_file`
  (`python_task_process_manager.py`). On Windows PyBreeze runs `json.dumps` on the string again. That
  makes the legacy flags and the double decode a contract, guarded by `test/unit_test/test_main.py`.
- **PyBreeze (in-process)**: `pybreeze/extend/mail_thunder_extend/mail_thunder_setting.py` imports
  `SMTPWrapper`, `read_output_content` and `get_mail_thunder_os_environ` to email HTML reports. Keep
  those names, the `mail_thunder_content.json` file name and the env var names stable.
- **TestPioneer** lists `je-mail-thunder` in its dependencies but does not import it.
- **Names inherited from AutoControl**:
  - the action-dict key was `auto_control` and is now `mail_thunder`, and the socket function is now
    `start_mail_thunder_socket_server`; both old names are deprecated aliases;
  - FileAutomation still uses both old names;
  - the default port is 9942, the free slot next to the sibling servers (AutoControl 9938, APITestka 9939,
    LoadDensity 9940, WebRunner 9941, FileAutomation 9943–9945); it was 9944, FileAutomation's HTTP
    action-server default. The Graph webhook listener takes 9946 and MailThunder Studio 9947.
- **Builtins policy**: the executor registers only the `SAFE_BUILTINS` allowlist (22 side-effect-free
  builtins such as `print`, `len`, `sorted`); `eval`, `exec`, `open`, `__import__`, `getattr` and the
  like are not commands. LoadDensity and WebRunner register the same allowlist, and APITestka registers no
  builtins (workspace X-12). JSON scripts that PyBreeze or users wrote against the old "every builtin"
  behaviour lose everything outside the allowlist.
- **ActionCore (this repo depends on it)**: `je_action_core` (Integration-Automation/ActionCore) holds the executor,
  registry, package manager, action-file reading and writing, file listing and the TCP action server. MailThunder
  configures them as follows:
  - **executor**: document key `mail_thunder`, legacy key `auto_control` (with a `DeprecationWarning`); an empty
    or non-list action list returns `{}` and logs `action_is_null_error`; `LegacyActionParser` with
    `cant_execute_action_error`; plain record keys; `LoggingReporter(mail_thunder_logger)`;
  - **registry**: functions only;
  - **package manager**: `<package>_<member>` names, dotted identifiers only, import and attribute errors
    logged, gate on (refusals raise `ExecuteActionException`);
  - **socket server**: `_validate_payload` runs first; `ValueError`, `OSError` and `TypeError` are answered;
    oversized payloads are dropped; messages go to the console.

  It is a PyPI dependency (`je_action_core>=0.0.1`; hash-locked for CI in `.github/requirements/test.txt`).
  ActionCore lists MailThunder in its own §6.

## 7. Design constraints

- Wrapper/Adapter pattern. Any class that holds a resource implements `__enter__` / `__exit__`
  (CLAUDE.md § Design Patterns & Software Engineering Principles › Required Patterns).
- `smtp_instance`, `imap_instance`, `mail_instance`, `executor` and `package_manager` are module-level singletons; do
  not create duplicates (§ Required Patterns).
- Every executable feature registers through `event_dict`. Extend with new commands instead of
  changing signatures (§ Engineering Principles).
- Credentials come only from `mail_thunder_content.json` or env vars. Never hardcode, log or commit
  them (§ Security Requirements › Credential Handling).
- SSL/TLS only: implicit TLS, or STARTTLS that must succeed before anything else is sent. OAuth2 token
  endpoints and web API providers must be `https`. The socket server, the Graph webhook listener and MailThunder Studio
  bind `localhost` by default (§ Security Requirements › Network
  Security).
- Validate input at boundaries. Sanitize file names in `output_all_mail_as_file` and attachments.
  Cap socket reads (§ Security Requirements › Input Validation).
- Login is deferred to `later_init()`; do not add new network work at import time (§ Performance
  Guidelines).
- Keep dependencies minimal and prefer the standard library (§ Security Requirements › Dependency
  Security).
- Log with `mail_thunder_logger`; `print()` is allowed only in the CLI and socket server. New
  exceptions subclass `MailThunderException` (§ Code Style).
- No dead code or compatibility shims (§ Dead Code Policy).
- Limits: cognitive complexity ≤ 15, cyclomatic complexity ≤ 10, functions ≤ 50 lines, modules ≤ 750
  lines, ≤ 7 parameters, lines ≤ 120 characters (§ Linter Compliance › Complexity & Size Limits).
- Commit format is `<type>: <description>` (§ Commit Convention).

## 8. When to update this file

- A subpackage under `je_mail_thunder/` or a facade export is added, removed or renamed.
- A provider name, the `MailSender` / `MailStore` interface, a `MailMessage` field or an `MT_mail_*` command changes.
- An event name, a `MailFilter` rule or the `MailTriggerBackend` interface changes.
- `__main__.py` flags, the Windows double decode, or the socket protocol (port, terminator,
  `quit_server`, payload limits) changes.
- A Studio route, its token or `Host` check, or its command line changes.
- The action format (`mail_thunder` key and its `auto_control` alias, `MT_` prefix), the builtins policy, or the import-time
  instance creation changes.
- The credential sources (file name, env var names, lookup order) or the `mail_provider` setting change.
- A release channel changes: which workflow publishes which package, or how its version is chosen.
- A §6 contract changes, for example PyBreeze's imports or its subprocess invocation.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
