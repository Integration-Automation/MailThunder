# progress.md: MailThunder

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-7, X-11, X-12, L-8).

## Open

- **#2** `pyproject.toml` has no `dependencies` field, and its header comment says "dev version" although the package name is the stable one.
- **#3** [DECIDE] Python floor is 3.9 while the other workspace libraries require 3.10.
- **#4** The socket-server entry is still named `start_autocontrol_socket_server` (copied from AutoControl).
- **#5** [DECIDE] OAuth2 support: Google and Microsoft are retiring basic authentication (workspace L-8).
- **#6** [UNVERIFIED] Importing the package opens SSL connections to the Gmail SMTP and IMAP servers; when a connection fails the instance becomes `None`, yet `Executor()` reads methods from both instances at import time (found by reading the code, not by running it). Connect lazily instead.
- **#7** The socket server's default port 9944 is also FileAutomation's HTTP action-server default; the server also takes host/port overrides from `sys.argv`. The action-dict key is `auto_control` and `smtp_quit` has no `MT_` prefix.
- **#8** [DECIDE] `MT_add_package_to_executor` lets any action list, including one sent to the socket server, load an importable package such as `os` or `subprocess` and call its functions (`je_mail_thunder/utils/package_manager/package_manager_class.py:69`), which bypasses the builtins allowlist. Restrict it (package allowlist, or not callable from socket input), or document it as trusted-input only (workspace X-12).
