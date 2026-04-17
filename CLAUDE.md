# CLAUDE.md — MailThunder

## Project Overview

MailThunder (`je_mail_thunder`) is a Python email automation library wrapping SMTP and IMAP4 protocols. It provides JSON-based scripting, project templates, and a socket server for remote execution.

- **Language**: Python 3.9+
- **Package**: `je_mail_thunder` (PyPI: `je-mail-thunder`)
- **License**: MIT
- **Entry point**: `je_mail_thunder/__main__.py`

## Build & Test

```bash
pip install -e .                  # Install in dev mode
pip install -r dev_requirements.txt
pytest                            # Run tests (testpaths = test/)
```

## Architecture

```
je_mail_thunder/
  smtp/smtp_wrapper.py      # SMTPWrapper (extends SMTP_SSL)
  imap/imap_wrapper.py      # IMAPWrapper (extends IMAP4_SSL)
  utils/
    executor/                # Command pattern — JSON action executor
    socket_server/           # TCP socket server for remote command execution
    save_mail_user_content/  # Credential storage (JSON file / env vars)
    project/template/        # Template method pattern for project scaffolding
    package_manager/         # Dynamic package loading
    json/                    # JSON file I/O
    json_format/             # JSON processing
    file_process/            # Directory file listing
    logging/                 # Centralized logger instance
    exception/               # Custom exception hierarchy
```

## Design Patterns & Software Engineering Principles

### Required Patterns

- **Wrapper / Adapter Pattern**: `SMTPWrapper` and `IMAPWrapper` extend stdlib classes to add logging, auto-login, and context manager support. New protocol wrappers must follow this pattern.
- **Command Pattern**: The `Executor` class maps string command names to callable actions. All new executable features must register through `event_dict`.
- **Template Method Pattern**: Project scaffolding uses `template_executor.py` / `template_keyword.py`. Extend templates by adding keyword handlers, not by modifying the base flow.
- **Singleton-like Module Instances**: `smtp_instance`, `imap_instance`, `executor`, `package_manager` are module-level singletons. Do not create duplicate global instances.
- **Context Manager Protocol**: All wrappers implement `__enter__` / `__exit__`. New resource-holding classes must do the same.

### Engineering Principles

- **Single Responsibility**: Each module under `utils/` handles one concern. Do not merge unrelated logic into a single module.
- **Open/Closed**: Extend behavior by adding new commands to `Executor.event_dict` or new template keywords — not by modifying existing method signatures.
- **DRY**: The login logic (`try_to_login_with_env_or_content`) is shared across SMTP/IMAP. If adding new auth sources, update the shared credential flow in `save_mail_user_content/`.
- **Fail Fast with Logging**: All public methods catch exceptions, log via `mail_thunder_logger`, and avoid silent failures. Follow this pattern for any new code.

## Performance Guidelines

- **Lazy Initialization**: `smtp_instance` and `imap_instance` are created at import time with try/except fallback to `None`. Use `later_init()` for deferred login — do not block module import with network calls.
- **Avoid Redundant I/O**: When processing multiple emails, prefer batch operations. Do not open/close connections per email.
- **Minimize Memory Allocation**: Use generators or iterators for large mailbox operations instead of building full lists in memory.
- **Connection Reuse**: Reuse `SMTPWrapper` / `IMAPWrapper` instances within a session. Do not create new connections for each send/receive operation.
- **File I/O**: Use context managers (`with` statements) for all file operations to ensure prompt resource release.

## Dead Code Policy

- **Remove unused imports, variables, functions, and classes** before committing. Do not leave commented-out code blocks.
- **No placeholder or stub code** unless explicitly required for an interface contract.
- **No backwards-compatibility shims** — if something is unused, delete it completely.
- Run a linter check before committing to catch unreferenced symbols.

## Security Requirements (Mandatory)

### Credential Handling
- **Never hardcode credentials** in source code. Credentials must come from `mail_thunder_content.json` (local, gitignored) or environment variables only.
- **Never log credentials**. Sanitize all log messages — ensure `user`, `password`, and token values are never written to `mail_thunder_logger` or stdout.
- **Never commit** `.env` files, `mail_thunder_content.json`, or any file containing secrets.

### Input Validation
- **Validate all external input** at system boundaries: JSON action files, socket server commands, CLI arguments, email headers.
- **Sanitize file paths** — use `os.path.basename()` and reject path traversal patterns (`..`, absolute paths) in user-supplied filenames, especially in `output_all_mail_as_file` and attachment handling.
- **Limit socket recv buffer** and validate JSON payloads before execution to prevent injection or denial-of-service.

### Command Execution Safety
- The `Executor` registers all Python builtins into `event_dict`. Be aware that this allows arbitrary builtin calls via JSON commands. Any new command registration via `add_command_to_executor` must validate that only `types.MethodType` or `types.FunctionType` are accepted (already enforced).
- **Never use `eval()` or `exec()`** on untrusted input.
- **Never use `subprocess.shell=True`** with user-provided strings.

### Network Security
- SMTP uses `SMTP_SSL` (port 465) — always use SSL/TLS. Do not downgrade to plain SMTP.
- IMAP uses `IMAP4_SSL` — always use SSL/TLS. Do not downgrade to plain IMAP.
- Socket server binds to `localhost` by default. Do not change the default bind address to `0.0.0.0` without explicit user configuration.

### Dependency Security
- Keep dependencies minimal (`requirements.txt` is intentionally small).
- Audit new dependencies before adding. Prefer stdlib solutions.

## Commit Convention

- Write concise commit messages that describe the "why", not just the "what".
- **Do not mention any AI assistant, model name, or tool name** (including but not limited to Claude, GPT, Copilot, etc.) in commit messages, PR descriptions, or code comments.
- **Do not include `Co-Authored-By` headers referencing AI tools.**
- Format: `<type>: <description>` (e.g., `fix: prevent path traversal in mail export`, `feat: add OAuth2 support for IMAP login`).
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `security`.

## Code Style

- Follow existing project conventions — no type annotations on code you didn't write unless fixing a bug there.
- Use `mail_thunder_logger` for all logging. No `print()` in library code (only in CLI/socket server output).
- Exception hierarchy rooted at `MailThunderException`. New exceptions must subclass it.
- All public methods need docstrings following the existing `:param` / `:return:` style.
