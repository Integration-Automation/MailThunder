# progress.md: MailThunder

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-12, L-8).

## Open

- **#3** [DECIDE] Python floor is 3.9 while the other workspace libraries require 3.10.
- **#5** [DECIDE] OAuth2 support: Google and Microsoft are retiring basic authentication (workspace L-8).
- **#7** `start_mail_thunder_socket_server` reads `sys.argv[1]`/`[2]` as host/port and lets them override its arguments (`je_mail_thunder/utils/socket_server/mail_thunder_socket_server.py`), so any host program started with one or two arguments rebinds the server. The action-dict key is `auto_control` (renaming it would break stored action files, so it needs an alias period).
- **#8** [DECIDE] `MT_add_package_to_executor` lets any action list, including one sent to the socket server, load an importable package such as `os` or `subprocess` and call its functions (`je_mail_thunder/utils/package_manager/package_manager_class.py:69`), which bypasses the builtins allowlist. Restrict it (package allowlist, or not callable from socket input), or document it as trusted-input only (workspace X-12).
