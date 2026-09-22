# MailThunder Architecture

> Short overview for people and agents.
> Last verified: 2026-09-22 against `221812f` on `dev`.

## 1. Purpose

MailThunder (`je_mail_thunder`, PyPI `je-mail-thunder`) is a small email automation library that
uses only the standard library. `pyproject.toml` builds `je_mail_thunder` and `dev.toml` builds
`je_mail_thunder_dev`. `SMTPWrapper` and `IMAPWrapper` extend `smtplib.SMTP_SSL` and
`imaplib.IMAP4_SSL` with credential lookup, logging and context-manager support. A JSON action
executor exposes the same operations to action files, a CLI and a TCP socket server.

## 2. Layers and directories

| Path | Responsibility |
| --- | --- |
| `je_mail_thunder/__init__.py` | Public facade (`__all__`) |
| `je_mail_thunder/__main__.py` | Legacy flag CLI (`python -m je_mail_thunder`) |
| `je_mail_thunder/smtp/smtp_wrapper.py` | `SMTPWrapper(SMTP_SSL)` (default `smtp.gmail.com:465`) and the module instance `smtp_instance` (a `LazyInstance`) |
| `je_mail_thunder/imap/imap_wrapper.py` | `IMAPWrapper(IMAP4_SSL)` (default `imap.gmail.com`) and the module instance `imap_instance` (a `LazyInstance`) |
| `je_mail_thunder/utils/executor/action_executor.py` | `Executor.event_dict` (`MT_*` commands plus the `SAFE_BUILTINS` allowlist), `execute_action`, `execute_files`, `add_command_to_executor` |
| `je_mail_thunder/utils/save_mail_user_content/` | Credential sources: `mail_thunder_content.json` in the working directory (`read_output_content` / `write_output_content`) and the env vars `mail_thunder_user` / `mail_thunder_user_password` (`set_/get_mail_thunder_os_environ`) |
| `je_mail_thunder/utils/socket_server/mail_thunder_socket_server.py` | TCP server `start_mail_thunder_socket_server` (old name `start_autocontrol_socket_server` kept as a deprecated alias) with payload validation (`_validate_payload`, `MAX_PAYLOAD_BYTES`, `MAX_ACTIONS`) |
| `je_mail_thunder/utils/package_manager/` | `package_manager`: loads an installed package's members into the executor |
| `je_mail_thunder/utils/project/` | `create_project_dir` scaffolding; `template/template_keyword.py` and `template_executor.py` hold the templates |
| `je_mail_thunder/utils/{json,json_format,file_process,logging,exception}/` | Action JSON I/O, JSON reformat, directory listing, `mail_thunder_logger` (file at `$MAIL_THUNDER_LOG_FILE` or `~/.je_mail_thunder/logs/Mail_Thunder.log`, opened on first use), `MailThunderException` hierarchy |
| `test/unit_test/` | pytest suite (`testpaths = ["test"]`). `manual_test/` holds scripts that need real mailboxes; its `conftest.py` excludes them from collection |
| `docs/source/` | Sphinx docs (`docs/Eng`, `docs/Zh`, `docs/API`) |

## 3. Entry points and public interfaces

- **Python facade**: `import je_mail_thunder` gives you:
  - wrappers: `SMTPWrapper`, `smtp_instance`, `IMAPWrapper`, `imap_instance`;
  - execution: `execute_action`, `execute_files`, `add_command_to_executor`, `read_action_json`,
    `get_dir_files_as_list`, `create_project_dir`;
  - credentials: `read_output_content`, `write_output_content`, `set_mail_thunder_os_environ`,
    `get_mail_thunder_os_environ`, `mail_thunder_content_data_dict`, `is_need_to_save_content`.
- **Action format**: an action is `[name]`, `[name, {kwargs}]` or `[name, [args]]`. A file holds a
  list of actions or `{"auto_control": [...]}`; the key came from AutoControl.
- **Commands**: examples are `MT_smtp_later_init`, `MT_smtp_create_message_and_send`,
  `MT_imap_select_mailbox`, `MT_imap_output_all_mail_as_file` and `MT_add_package_to_executor`.
  `MT_smtp_quit` closes the SMTP connection; its pre-prefix name `smtp_quit` is still registered.
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
- There is no MCP server, LSP, pytest plugin or GUI.

## 4. Main flows

**Action → mail server**

```
action JSON / --execute_str → __main__ → execute_action → Executor._execute_event
  → event_dict["MT_*"] → deferred call on smtp_instance / imap_instance (connects on first use) → smtplib / imaplib over SSL
  → record dict {"execute: <action>": return value | repr(error)} → mail_thunder_logger
```

**Login**

```
MT_smtp_later_init / MT_imap_later_init → try_to_login_with_env_or_content → _resolve_credentials
  → read_output_content() (./mail_thunder_content.json) else get_mail_thunder_os_environ() → login()
```

**Socket**: TCP client → `TCPServerHandler.handle` (8192-byte cap, `_validate_payload`) →
`execute_action` → return values, then `Return_Data_Over_JE`.

**Import-time behaviour**: importing opens no connection. `smtp_instance` and `imap_instance` are
`LazyInstance` proxies (`utils/lazy_instance/lazy_instance.py`) that build the real `SMTPWrapper` /
`IMAPWrapper` — and so connect — the first time anything is read from them; a connection failure
raises there, at use, and the next use retries. `Executor.__init__` registers `deferred(instance,
"method")` callables, which look the method up only when the action runs, so building the executor
does not connect either. Login still waits until `later_init`.

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
- **New credential source**: extend `save_mail_user_content/` and both `_resolve_credentials` helpers
  (SMTP and IMAP).
- **Project template keyword**: edit `utils/project/template/template_keyword.py` /
  `template_executor.py`, which are wired from `utils/project/create_project_structure.py`.

## 6. Cross-project boundaries

- **PyBreeze (subprocess)**: `call_mail_thunder` (`PyBreeze/pybreeze/extend/process_executor/mail_thunder/mail_thunder_process.py`)
  → `build_process(..., "je_mail_thunder", ...)` → `python -m je_mail_thunder --execute_str/--execute_file`
  (`python_task_process_manager.py`). On Windows PyBreeze runs `json.dumps` on the string again. That
  makes the legacy flags and the double decode a contract, guarded by `test/unit_test/test_main.py`.
- **PyBreeze (in-process)**: `pybreeze/extend/mail_thunder_extend/mail_thunder_setting.py` imports
  `SMTPWrapper`, `read_output_content` and `get_mail_thunder_os_environ` to email HTML reports. Keep
  those names, the `mail_thunder_content.json` file name and the env var names stable.
- **TestPioneer** lists `je-mail-thunder` in its dependencies but does not import it.
- **Names inherited from AutoControl**:
  - the action-dict key is `auto_control` (the socket function is now `start_mail_thunder_socket_server`;
    the old name is a deprecated alias);
  - FileAutomation uses the same function name and key;
  - the default port is 9942, the free slot next to the sibling servers (AutoControl 9938, APITestka 9939,
    LoadDensity 9940, WebRunner 9941, FileAutomation 9943–9945); it was 9944, FileAutomation's HTTP
    action-server default.
- **Builtins policy**: the executor registers only the `SAFE_BUILTINS` allowlist (22 side-effect-free
  builtins such as `print`, `len`, `sorted`); `eval`, `exec`, `open`, `__import__`, `getattr` and the
  like are not commands. LoadDensity and WebRunner instead blacklist `_UNSAFE_BUILTINS`, and APITestka
  registers no builtins (workspace X-12). JSON scripts that PyBreeze or users wrote against the old
  "every builtin" behaviour lose everything outside the allowlist.

## 7. Design constraints

- Wrapper/Adapter pattern. Any class that holds a resource implements `__enter__` / `__exit__`
  (CLAUDE.md § Design Patterns & Software Engineering Principles › Required Patterns).
- `smtp_instance`, `imap_instance`, `executor` and `package_manager` are module-level singletons; do
  not create duplicates (§ Required Patterns).
- Every executable feature registers through `event_dict`. Extend with new commands instead of
  changing signatures (§ Engineering Principles).
- Credentials come only from `mail_thunder_content.json` or env vars. Never hardcode, log or commit
  them (§ Security Requirements › Credential Handling).
- SSL/TLS only. The socket server binds `localhost` by default (§ Security Requirements › Network
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
- `__main__.py` flags, the Windows double decode, or the socket protocol (port, terminator,
  `quit_server`, payload limits) changes.
- The action format (`auto_control` key, `MT_` prefix), the builtins policy, or the import-time
  instance creation changes.
- The credential sources (file name, env var names, lookup order) change.
- A §6 contract changes, for example PyBreeze's imports or its subprocess invocation.
- A CLAUDE.md section referenced in §7 is renamed or its rule changes.
- Refresh the "Last verified" line whenever this file is re-checked against HEAD.
