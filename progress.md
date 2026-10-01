# progress.md: MailThunder

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-12, X-13, L-8).

## Open

- **#5** [DECIDE] OAuth2 support: Google and Microsoft are retiring basic authentication (workspace L-8).
- **#8** [DECIDE] `MT_add_package_to_executor` lets any action list, including one sent to the socket server, load an importable package such as `os` or `subprocess` and call its functions (`je_mail_thunder/utils/package_manager/package_manager_class.py`), which bypasses the builtins allowlist. je_action_core's package gate is one setting away: set `gate=PackageGate.ON` there, add `executor.allow_packages` / `set_allow_arbitrary_packages` and the README and docs text, as APITestka did (its U-20261001-16). Or document the command as trusted-input only (workspace X-12).
- **#9** [BLOCKED: je_action_core on PyPI, ActionCore `progress.md` #1] Install `je_action_core` from PyPI instead of the GitHub pin.
  - Add it to `.github/requirements/test.in` and `publish.in`, regenerate the `.txt` files, and drop the "Install je_action_core" step from `test_dev.yml`, `test_stable.yml` and `publish_stable.yml`.
  - Until then, do not release `main`: the published metadata requires `je_action_core`, which PyPI does not have yet.
