# docs/updates: update log index

`progress.md` holds only work that is **not done yet**. Everything that *was* done (what changed, measured numbers, decisions, snapshots) is recorded here: **one batch file per month**, one entry per piece of work, each entry with a fixed-format ID and tags, and one row per entry in the index below.

> No TODOs here. If an entry mentions something still open, it only points to it (e.g. "open item: `progress.md` #3"); the item itself lives in `progress.md`.

## How to query

Run from the repository root:

| To find | Command |
|---|---|
| every entry, one line each | `rg -n "^## U-2" docs/updates` |
| entries of one type | `rg -n "^## U-2.*#done" docs/updates` |
| entries with a topic tag | `rg -n "^## U-2.*#<tag>" docs/updates` |
| one day or one month | `rg -n "^## U-202609" docs/updates` |
| the full text of one entry | `rg -n -A 60 "^## U-20260922-01" docs/updates` |
| any keyword | `rg -n "keyword" docs/updates` |

Without `rg`: `git grep -n "^## U-2" -- docs/updates`, or in PowerShell `Select-String -Path docs/updates/*.md -Pattern '^## U-2'`.

## Entry format

```markdown
## U-YYYYMMDD-NN · YYYY-MM-DD · one-line title · #type #topic

- **What**: ...
- **Result / numbers**: ...
- **Files**: `path` ...
- **Evidence**: commit, file:line, link ...
- **Open items**: none / see `progress.md` ...
```

- **ID**: `U-` + date + two-digit sequence for that day. IDs are never renumbered or reused, so code comments and other documents can cite them.
- **Type tag** (exactly one): `#done` finished `progress.md` item, `#snapshot` measurement or inventory, `#decision`, `#incident`, `#migration`, `#docs`, `#release`.
- Topic tags are free-form (`#mcp`, `#wayland`, ...).
- Keep conclusions, numbers, files and evidence; drop the reasoning trail and dead ends.

## Batch rules

1. One file per month: `docs/updates/YYYY-MM.md`. Append new entries at the end.
2. Over about 800 lines, continue in `YYYY-MM-b.md` (then `-c`) and list it in the batch table below.
3. **Claim the ID under a lock.** Several sessions may write this log at the same time (for example parallel autonomous runs), and without a lock two of them pick the same number:
   1. `mkdir docs/updates/.id-lock`. Creating a directory is atomic, so only one writer succeeds. If it already exists, someone else is claiming: wait a few seconds and retry. A lock older than 10 minutes is stale and may be removed.
   2. Find the day's last number with `rg -n "^## U-YYYYMMDD" docs/updates` and write the heading line and the index row.
   3. `rmdir docs/updates/.id-lock`, then fill in the body. Git never tracks the empty lock directory.
   4. Before committing, `rg -c "^## U-<your ID>" docs/updates` must report one match in total. If not, renumber your entry under the lock and fix its index row. Whoever merges a branch renumbers entries that reuse an ID.
4. **One line per index row**: title only (about 60 characters), no summary.
5. Never rewrite a recorded entry. Correct it with a new `#decision` or `#incident` entry and add "→ corrected in U-..." to the old one.

## When a `progress.md` item is done

In the same commit: delete the item from `progress.md`, add a `#done` entry here that names it, and add its index row.

---

## Index (newest first)

| ID | Date | Title | Tags | Batch |
|---|---|---|---|---|
| U-20261008-10 | 2026-10-08 | Project mail layer: a project's mail/ directory and project_mail() | #done #project-layer #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-09 | 2026-10-08 | Audit log, provider health, event webhooks, and more providers | #done #monitoring #providers #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-08 | 2026-10-08 | Microsoft Graph provider with polling and webhook trigger backends | #done #providers #graph #triggers #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-07 | 2026-10-08 | Mail events and triggers: mail.on, filters, polling and IMAP IDLE backends | #done #triggers #events #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-06 | 2026-10-08 | Mail templates with a Jinja2-style language in the standard library | #done #templates #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-05 | 2026-10-08 | SMTP wrappers check attachments; exported mail keeps its body on Windows | #done #bugfix #attachments #windows | [2026-10](2026-10.md) |
| U-20261008-04 | 2026-10-08 | PyPI metadata: description, keywords, classifiers and project URLs | #done #packaging #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-03 | 2026-10-08 | Core mail API: Mail over a provider interface, with SMTP and IMAP providers | #done #api #providers #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-02 | 2026-10-08 | Authentication abstraction: one interface for password and OAuth2 logins | #done #auth #oauth2 #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261008-01 | 2026-10-08 | Attachment policy checks attachments before a message is sent | #feature #attachments #security #roadmap-2.0 | [2026-10](2026-10.md) |
| U-20261001-09 | 2026-10-01 | The publish jobs build with the locked setuptools instead of downloading the newest | #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-08 | 2026-10-01 | Dependabot watches the hash-locked requirements; a guard keeps the publish jobs on them | #ci #security #X-13 | [2026-10](2026-10.md) |
| U-20261001-07 | 2026-10-01 | CI publishes je_mail_thunder_dev from the dev branch | #release #ci #X-13 | [2026-10](2026-10.md) |
| U-20261001-06 | 2026-10-01 | OAuth2 (XOAUTH2) login for Google and Microsoft, and SMTP over STARTTLS | #done #security #oauth2 #L-8 | [2026-10](2026-10.md) |
| U-20261001-05 | 2026-10-01 | je_action_core comes from PyPI | #done #build #L-6 | [2026-10](2026-10.md) |
| U-20261001-04 | 2026-10-01 | Package gate in front of MT_add_package_to_executor | #done #security #X-12 | [2026-10](2026-10.md) |
| U-20261001-03 | 2026-10-01 | je_action_core pin moves to 19bfe0a | #build #L-6 | [2026-10](2026-10.md) |
| U-20261001-02 | 2026-10-01 | Executor and its helpers move to je_action_core | #migration #executor #L-6 | [2026-10](2026-10.md) |
| U-20261001-01 | 2026-10-01 | Every workflow job has a timeout | #ci #tests | [2026-10](2026-10.md) |
| U-20260925-03 | 2026-09-25 | Python classifiers list every version CI tests | #packaging #tests | [2026-09](2026-09.md) |
| U-20260925-02 | 2026-09-25 | License metadata uses the SPDX expression | #packaging | [2026-09](2026-09.md) |
| U-20260925-01 | 2026-09-25 | Dependabot waits 7 days before proposing a new release | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260924-02 | 2026-09-24 | Keep checkout credentials only in the job that pushes | #ci #security | [2026-09](2026-09.md) |
| U-20260924-01 | 2026-09-24 | Move CI to Node 24 actions pinned by commit | #ci #security #deps | [2026-09](2026-09.md) |
| U-20260923-11 | 2026-09-23 | main merged into dev; CI hash-locked; dev merged into main | #done #ci #release | [2026-09](2026-09.md) |
| U-20260923-10 | 2026-09-23 | Action documents use a mail_thunder key; auto_control is deprecated | #done #api | [2026-09](2026-09.md) |
| U-20260923-09 | 2026-09-23 | Every text file is read and written as UTF-8 | #bugfix #encoding | [2026-09](2026-09.md) |
| U-20260923-08 | 2026-09-23 | Python 3.10 is the floor; CI tests 3.10 to 3.14 | #done #packaging #ci | [2026-09](2026-09.md) |
| U-20260923-07 | 2026-09-23 | The socket server no longer reads sys.argv | #change #socket #security | [2026-09](2026-09.md) |
| U-20260923-06 | 2026-09-23 | Socket server default port moves to 9942 | #change #socket | [2026-09](2026-09.md) |
| U-20260923-05 | 2026-09-23 | Mail_Thunder.log moves out of the working directory | #done #logging | [2026-09](2026-09.md) |
| U-20260923-04 | 2026-09-23 | MT_smtp_quit joins the other MT_ commands | #done #api | [2026-09](2026-09.md) |
| U-20260923-03 | 2026-09-23 | Socket server gets its own name; the AutoControl one is deprecated | #done #api | [2026-09](2026-09.md) |
| U-20260923-02 | 2026-09-23 | pyproject.toml declares no dependencies and names its channel | #done #packaging | [2026-09](2026-09.md) |
| U-20260923-01 | 2026-09-23 | Importing no longer connects to Gmail or fails offline | #done #bugfix | [2026-09](2026-09.md) |
| U-20260922-05 | 2026-09-22 | Legacy CLI tests cover what PyBreeze and TestPioneer call | #done #tests | [2026-09](2026-09.md) |
| U-20260922-04 | 2026-09-22 | Point project URLs at the current repository | #done #metadata | [2026-09](2026-09.md) |
| U-20260922-03 | 2026-09-22 | Executor registers only an allowlist of builtins | #done #security | [2026-09](2026-09.md) |
| U-20260922-02 | 2026-09-22 | Stop tracking .idea/ | #done #housekeeping | [2026-09](2026-09.md) |
| U-20260922-01 | 2026-09-22 | Adopt progress/architecture/docs-updates rules | #docs #migration | [2026-09](2026-09.md) |

## Batches

| File | Period | Entries |
|---|---|---:|
| [2026-10.md](2026-10.md) | 2026-10 | 19 |
| [2026-09.md](2026-09.md) | 2026-09 | 21 |
