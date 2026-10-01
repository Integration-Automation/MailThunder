# progress.md: MailThunder

Outstanding work only. When an item is done, delete it in the same commit and add a `#done` entry to `docs/updates/` (format and query commands: `docs/updates/README.md`). No finished items, no history, no rules (rules live in `CLAUDE.md`).
Item numbers (`#n`) are never reused. Tags: [DECIDE] needs the owner's decision, [BLOCKED] waits on something else, [UNVERIFIED] observed but not confirmed.
Cross-repo and workspace items live in `D:\Codes\progress.md` (relevant here: X-12, X-13, L-8).

## Open

- **#5** [DECIDE] OAuth2 support: Google and Microsoft are retiring basic authentication (workspace L-8).
- **#10** [BLOCKED: two releases must ship the warning first] Flip the package gate's default to refuse packages outside the allowlist.
  - Where: set `self.allow_arbitrary_packages = False` in `PackageManager.__init__` (`je_mail_thunder/utils/package_manager/package_manager_class.py`); the warning branch is je_action_core's `_check_allowed` and stays for the other projects.
  - Docs: the "Package gate" paragraph in the three READMEs and the "Package Gate" section of `docs/source/docs/{Eng,Zh}/package_manager.rst`.
  - Timing: the warning is first released in the version after 0.0.29 (`origin/main` `pyproject.toml`); flip once two releases after that one have shipped it.
  - Decide first: how a user who only runs action files (`python -m je_mail_thunder -e`, the socket server) allows a package without a Python host to call `executor.allow_packages(...)`.
