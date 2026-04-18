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

## Linter Compliance (SonarQube / Codacy / Pylint / Flake8)

All code must pass static analysis from SonarQube, Codacy, Pylint, and Flake8. The rules below encode the most common quality-gate failures for this codebase — follow them proactively rather than waiting for a linter report.

### Complexity & Size Limits
- **Cognitive Complexity ≤ 15** per function (SonarQube `python:S3776`). Refactor deeply nested conditionals into early-returns or helper functions.
- **Cyclomatic Complexity ≤ 10** per function (Pylint `R0912`). Split branchy logic.
- **Function length ≤ 50 lines**, **class length ≤ 300 lines**, **module length ≤ 750 lines** (SonarQube defaults). Decompose longer units.
- **Parameters ≤ 7** per function (Pylint `R0913`). Group related arguments into dataclasses or dicts.
- **Max line length: 120 characters** (Flake8 `E501`, configured project-wide).
- **Max nesting depth ≤ 4** (SonarQube `python:S134`).

### Naming (PEP 8 / Pylint `C0103`)
- `snake_case` for functions, methods, variables, modules; `PascalCase` for classes; `UPPER_SNAKE_CASE` for module-level constants.
- No single-letter names except loop counters (`i`, `j`, `k`) or well-known math conventions.
- Avoid shadowing builtins (`list`, `dict`, `id`, `type`, `input`, `file`) — SonarQube `python:S5806`.

### Exception Handling (SonarQube / Bandit)
- **Never use bare `except:`** — always catch specific exceptions (SonarQube `python:S5754`, Bandit `B110`).
- **Do not swallow exceptions silently**. Log via `mail_thunder_logger.error(...)` and re-raise or convert to a `MailThunderException` subclass.
- **Do not use `except Exception as e: pass`** — Codacy `PyLint-W0702/W0703`.
- Chain exceptions with `raise NewError(...) from original_error` to preserve traceback (SonarQube `python:S5708`).

### Duplication & Dead Code
- **No duplicated blocks ≥ 3 lines** (SonarQube `python:S4144` / `common-py:DuplicatedBlocks`). Extract shared logic into helpers.
- **No unused imports / variables / parameters / private functions** (Pylint `W0611`, `W0612`, `W0613`, `W0238`).
- **No unreachable code** after `return` / `raise` / `break` (SonarQube `python:S1763`).
- **No commented-out code** (SonarQube `python:S125`).
- **No `TODO` / `FIXME` without an issue reference** (SonarQube `python:S1135`). Either fix it or file a ticket and reference it.

### Comparison & Logic Correctness
- Use `is None` / `is not None` rather than `== None` (Pylint `C0121`, SonarQube `python:S5727`).
- Use `isinstance(x, T)` instead of `type(x) == T` (Pylint `C0123`).
- Do not compare boolean literals with `==` (`if flag:` not `if flag == True:`) — SonarQube `python:S1125`.
- No constant conditions in `if` / `while` (SonarQube `python:S1145`).
- No identical expressions on both sides of binary operators (SonarQube `python:S1764`).

### Mutable Defaults & Side Effects
- **Never use mutable default arguments** (`def f(x=[])`) — Pylint `W0102`, SonarQube `python:S5717`. Use `None` and initialize inside the function.
- No side effects at import time beyond logger setup and module-level singleton construction that already exists in this project.

### Security Hotspots (Bandit / SonarQube)
- **No hardcoded credentials / tokens / IPs** (Bandit `B105`-`B107`, SonarQube `python:S2068`).
- **No `assert` for runtime validation** — asserts are stripped in optimized mode (Bandit `B101`).
- **No `pickle` / `marshal` / `shelve` on untrusted data** (Bandit `B301`).
- **No `yaml.load` without `SafeLoader`** (Bandit `B506`).
- **No weak hashing** (`md5`, `sha1`) for security purposes (Bandit `B303`, `B324`).
- **No `random` module for security tokens** — use `secrets` (Bandit `B311`).
- **No `tempfile.mktemp`** — use `NamedTemporaryFile` (Bandit `B306`).
- **No binding to `0.0.0.0`** without explicit user opt-in (Bandit `B104`).
- **No SSL context disabling cert verification** (Bandit `B501`).
- **No XML parsing with `xml.etree` / `xml.sax` / `minidom`** on untrusted input — use `defusedxml` (Bandit `B314`-`B320`).

### Imports & Structure
- No wildcard imports (`from x import *`) outside `__init__.py` re-export (Pylint `W0401`).
- No relative imports beyond one level (`from ..x`). Prefer absolute (`from je_mail_thunder.x`).
- Imports ordered: stdlib, third-party, local — separated by blank lines (Flake8 `isort`).
- No circular imports (Pylint `R0401`).

### Formatting
- 4-space indentation, no tabs (Flake8 `W191`).
- Two blank lines between top-level defs, one blank line between methods (PEP 8 / Flake8 `E302`/`E303`).
- No trailing whitespace (Flake8 `W291`), files end with a single newline (Flake8 `W292`).
- No multiple statements on one line (Flake8 `E701`/`E702`).

### Documentation
- Every public module, class, and function has a docstring (Pylint `C0111` / `missing-docstring`). Use `:param` / `:return:` / `:raises:` style already in use.
- No misleading docstrings — update them when behavior changes.

### Enforcement Workflow
- Before committing: run `pip install pylint flake8 bandit` and locally execute `pylint je_mail_thunder`, `flake8 je_mail_thunder`, `bandit -r je_mail_thunder`.
- Treat any new SonarQube / Codacy finding on changed lines as a blocker. Do not suppress rules (`# noqa`, `# pylint: disable=`) without a comment explaining why and which specific rule is being suppressed.
