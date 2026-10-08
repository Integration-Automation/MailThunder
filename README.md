# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** is a lightweight and flexible email automation tool for Python. Its provider-agnostic `Mail` API sends and reads mail the same way whatever the provider; it wraps SMTP and IMAP4 protocols, provides a JSON-based scripting engine and project templates, and makes sending, receiving, and managing email content effortless.

**[繁體中文](README/README_zh-TW.md)** | **[简体中文](README/README_zh-CN.md)**

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Configuration](#configuration)
  - [Sending an Email (SMTP)](#sending-an-email-smtp)
  - [Sending an Email with Attachment](#sending-an-email-with-attachment)
  - [Reading Emails (IMAP)](#reading-emails-imap)
  - [Exporting All Emails to Files](#exporting-all-emails-to-files)
- [Core Mail API](#core-mail-api)
  - [Sending Mail](#sending-mail)
  - [Reading, Drafts and Deleting](#reading-drafts-and-deleting)
  - [Accounts and Providers](#accounts-and-providers)
  - [Errors](#errors)
  - [Moving from the Wrappers](#moving-from-the-wrappers)
- [Authentication](#authentication)
  - [JSON Config File](#json-config-file)
  - [Environment Variables](#environment-variables)
  - [OAuth2 (Google and Microsoft)](#oauth2-google-and-microsoft)
  - [Authentication Objects](#authentication-objects)
- [Attachment Policy](#attachment-policy)
- [Scripting Engine](#scripting-engine)
  - [Action JSON Format](#action-json-format)
  - [Available Script Commands](#available-script-commands)
  - [Extending with Custom Commands](#extending-with-custom-commands)
  - [Dynamic Package Loading](#dynamic-package-loading)
- [Project Templates](#project-templates)
- [Command-Line Interface](#command-line-interface)
- [Socket Server](#socket-server)
- [API Reference](#api-reference)
  - [Mail](#mail)
  - [SMTPWrapper](#smtpwrapper)
  - [SMTPStartTLSWrapper](#smtpstarttlswrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor Functions](#executor-functions)
  - [Utility Functions](#utility-functions)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

- **Provider-agnostic `Mail` API** — One object sends, reads, drafts and deletes mail, behind a provider interface new backends plug into (SMTP and IMAP today)
- **SMTP support** — Send emails over implicit TLS with Gmail (default) or any SMTP provider, or over STARTTLS (Microsoft 365)
- **IMAP4 support** — Read, search, and export emails via IMAP4 SSL
- **Attachment handling** — Automatically detect MIME types for text, image, audio, and binary files
- **Attachment policy** — Check the count, size, extension and MIME type of attachments before a message is sent, with a structured exception for each rule
- **HTML email** — Send HTML-formatted emails with attachments
- **JSON scripting engine** — Automate email workflows using JSON action files
- **Project templates** — Scaffold projects with pre-built keyword and executor templates
- **Socket server** — Control MailThunder remotely via TCP socket commands
- **Package manager** — Dynamically load Python packages into the scripting executor
- **Environment variable auth** — Authenticate via config file or OS environment variables
- **OAuth2 login** — SASL `XOAUTH2` for Gmail and Microsoft 365, with refresh-token exchange and a token cache in the standard library
- **Authentication objects** — `PasswordAuth`, `AppPasswordAuth`, `OAuth2Auth` and `XOAUTH2Auth` behind one `Authentication` interface
- **Auto-export** — Export all mailbox emails to local files in one call
- **Context manager support** — Use `with` statement for both SMTP and IMAP connections
- **Logging** — Built-in logging for all operations

---

## Requirements

- Python 3.10 or later
- `je_action_core`, installed with it: the action executor MailThunder shares with APITestka, LoadDensity and FileAutomation (it uses only the Python standard library)

---

## Installation

**Stable release:**

```bash
pip install je_mail_thunder
```

**Development release:**

```bash
pip install je_mail_thunder_dev
```

`je_mail_thunder_dev` follows the `dev` branch: CI publishes a new version each time a push to `dev`
passes the tests and changes what the package ships.

---

## Quick Start

### Configuration

Before using MailThunder, you need to set up authentication. Create a file named `mail_thunder_content.json` in your current working directory:

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

> **Important:** If you are using Gmail, you must use an [App Password](https://support.google.com/accounts/answer/185833), not your regular Google account password. You also need to [enable IMAP](https://support.google.com/mail/answer/7126229?hl=en) in your Gmail settings.

### Sending an Email (SMTP)

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()  # Log in using config file or env vars
    smtp.create_message_and_send(
        message_content="Hello from MailThunder!",
        message_setting_dict={
            "Subject": "Test Email",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        }
    )
```

### Sending an Email with Attachment

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()
    smtp.create_message_with_attach_and_send(
        message_content="Please see the attached file.",
        message_setting_dict={
            "Subject": "Email with Attachment",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        },
        attach_file="/path/to/file.pdf",
        use_html=False  # Set True if message_content is HTML
    )
```

### Reading Emails (IMAP)

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()  # Log in
    imap.select_mailbox("INBOX")
    emails = imap.mail_content_list()
    for mail in emails:
        print(f"Subject: {mail['SUBJECT']}")
        print(f"From: {mail['FROM']}")
        print(f"Body: {mail['BODY'][:100]}...")
```

### Exporting All Emails to Files

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()
    imap.select_mailbox("INBOX")
    imap.output_all_mail_as_file()  # Saves each email as a file named by subject
```

---

## Core Mail API

`Mail` is the provider-agnostic API: the same calls send, read, draft and delete mail whatever the account's provider
is. It uses the credentials described under [Authentication](#authentication), connects on first use, keeps the
connection for the calls that follow, and raises an exception when something fails instead of only logging it.

### Sending Mail

```python
from je_mail_thunder import Mail

with Mail() as mail:                       # Gmail, or the provider the OAuth2 settings name
    mail.send(
        to="receiver@example.com",         # one address, several separated by commas, or a list
        cc=["team@example.com"],
        subject="Nightly report",
        text="42 passed, 0 failed.",
        html="<b>42</b> passed, 0 failed.",
        attachments=["report.html"],
    )
```

With both `text` and `html`, the message carries the two as alternatives. The sender is the account's user unless
`sender=` is given; `bcc`, `reply_to` and `headers` are accepted too. Before anything reaches the server the message
is checked: at least one recipient, valid addresses, a one-line subject and one-line header values (so a value cannot
smuggle in a second header), and the attachments against the [attachment policy](#attachment-policy)
(`Mail(policy=...)`; 25 MiB of any type by default).

### Reading, Drafts and Deleting

```python
from je_mail_thunder import Mail

with Mail() as mail:
    for message in mail.get_messages(folder="INBOX", limit=10, unread_only=True):
        print(message.message_id, message.sender, message.subject)
        for attachment in message.attachments:
            attachment.save("downloads")    # under a name that cannot leave the directory

    message = mail.get_message("4321")      # by the message_id get_messages gave
    mail.create_draft(to="receiver@example.com", subject="Later", text="...")
    mail.delete_message("4321")
```

`get_messages` returns an iterator, newest first: messages are fetched one at a time, so a large mailbox is never held
in memory, and reading does not mark a message as read. `query=` takes a search in the provider's own syntax (IMAP
`SEARCH` criteria such as `'FROM "ci@example.com" SINCE 1-Oct-2026'`). Each message is a `MailMessage` with `subject`,
`sender`, `to`, `cc`, `reply_to`, `date`, `text`, `html`, `attachments`, `headers` and `message_id`.

### Accounts and Providers

```python
from je_mail_thunder import AppPasswordAuth, Mail, MailAccount, MailServers

Mail(provider="microsoft")                  # Microsoft 365; login from the config file or the environment
Mail(provider="gmail", auth=AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop"))
Mail(account=MailAccount(                   # any other SMTP / IMAP server
    provider="smtp",
    auth=AppPasswordAuth("you@example.com", "..."),
    servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"),
))
```

| Provider name | Sends over | Reads over |
|---|---|---|
| `google` (or `gmail`) | SMTP, `smtp.gmail.com:465`, implicit TLS | IMAP, `imap.gmail.com` |
| `microsoft` | SMTP, `smtp.office365.com:587`, STARTTLS | IMAP, `outlook.office365.com` |
| `smtp` | SMTP on the account's `MailServers` (implicit TLS on 465, or `smtp_starttls=True` on 587) | IMAP on the account's `MailServers` |

Without a provider name, `Mail()` uses the provider the OAuth2 settings name, else Gmail: the same servers
`smtp_instance` and `imap_instance` use. Connections always use TLS. A new backend implements `MailSender` and / or
`MailStore` and is added with `register_provider(name, factory)`; `Mail` and the code that uses it stay the same.

### Errors

Every failure is logged and raised as a `MailThunderException` subclass
(`je_mail_thunder.utils.exception.exceptions`):

| Exception | Meaning |
|---|---|
| `MailThunderMessageException` | the message cannot be sent as it is: no recipient, no sender, an invalid address or header |
| `MailThunderAttachmentException` | an attachment is missing or breaks the policy |
| `MailThunderAuthenticationException` | there are no credentials, or the server refused the login |
| `MailThunderConnectionException` | the server could not be reached, or the connection was lost |
| `MailThunderSendException` | the server refused the message, or some of its recipients (`refused`) |
| `MailThunderProviderException` | base of the two above; also an unknown provider, a refused folder or an unknown message id |

A message is never sent twice: a failure while sending is reported, not retried. A connection the server dropped
while it sat idle is replaced before the next call.

### Moving from the Wrappers

`SMTPWrapper`, `IMAPWrapper`, `smtp_instance`, `imap_instance` and the `MT_smtp_*` / `MT_imap_*` commands keep working
as before, so code can move one call at a time:

| Wrapper call | `Mail` call |
|---|---|
| `smtp.later_init()` / `imap.later_init()` | not needed: `Mail` logs in on first use |
| `smtp.create_message_and_send(content, settings)` | `mail.send(to=..., subject=..., text=content)` |
| `smtp.create_message_with_attach_and_send(content, settings, file, use_html=True)` | `mail.send(to=..., subject=..., html=content, attachments=[file])` |
| `imap.select_mailbox("INBOX")` then `imap.mail_content_list()` | `mail.get_messages(folder="INBOX")` |
| `smtp.quit()` / `imap.quit()` | `mail.close()`, or `with Mail() as mail:` |

```python
from je_mail_thunder import Mail, legacy_message, mail_from_wrappers, smtp_instance

# The arguments of create_message_and_send / create_message_with_attach_and_send, as a message
message = legacy_message("Hello", {"Subject": "Hi", "From": "me@gmail.com", "To": "you@example.com"},
                         attach_file="report.pdf", use_html=False)
Mail().send(message)

# Or keep a wrapper that is already logged in, and send through it with the checks Mail adds
smtp_instance.later_init()
mail_from_wrappers(smtp=smtp_instance).send(message)
```

What differs: `Mail` raises where the wrapper methods log the error and return `None`; a message needs at least one
valid recipient; attachments are checked against the policy; reading does not mark messages as read and gives
`MailMessage` objects instead of `{"SUBJECT": ..., "BODY": ...}` dicts.

---

## Authentication

MailThunder logs in with a password or with OAuth2. It reads the JSON config file first, then the environment variables; OAuth2 settings, when present, are used instead of a password.

### JSON Config File

Place `mail_thunder_content.json` in the current working directory:

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

### Environment Variables

Set these environment variables before running your script:

```python
from je_mail_thunder import set_mail_thunder_os_environ

set_mail_thunder_os_environ(
    mail_thunder_user="your_email@gmail.com",
    mail_thunder_user_password="your_app_password"
)
```

Or set them in your shell:

```bash
export mail_thunder_user="your_email@gmail.com"
export mail_thunder_user_password="your_app_password"
```

### OAuth2 (Google and Microsoft)

Google and Microsoft are retiring password logins for mail. With OAuth2, MailThunder exchanges a refresh token for a
short-lived access token at the provider's token endpoint (standard library only, `https` required) and logs in with
SASL `XOAUTH2`. Get the client ID, client secret and refresh token once through the provider's consent flow (a Google
Cloud OAuth client, or a Microsoft Entra app registration); MailThunder does not run that flow.

In `mail_thunder_content.json`:

```json
{
  "user": "you@example.com",
  "oauth2": {
    "provider": "microsoft",
    "client_id": "...",
    "client_secret": "...",
    "refresh_token": "...",
    "tenant": "common"
  }
}
```

Or in the environment: `mail_thunder_user` plus `mail_thunder_oauth2_provider`, `mail_thunder_oauth2_client_id`, `mail_thunder_oauth2_client_secret`, `mail_thunder_oauth2_refresh_token`; optionally `mail_thunder_oauth2_tenant`, `mail_thunder_oauth2_scope`, `mail_thunder_oauth2_token_url`, `mail_thunder_oauth2_access_token` (a token used as given).

| Provider | SMTP | IMAP | Scope it asks for |
|---|---|---|---|
| `google` (default) | `smtp.gmail.com:465`, implicit TLS (`SMTPWrapper`) | `imap.gmail.com` | `https://mail.google.com/` |
| `microsoft` | `smtp.office365.com:587`, STARTTLS (`SMTPStartTLSWrapper`) | `outlook.office365.com` | `SMTP.Send`, `IMAP.AccessAsUser.All` on `https://outlook.office.com/`, `offline_access` |

`smtp_instance` and `imap_instance`, and so the `MT_smtp_*` / `MT_imap_*` commands, connect to the servers of the
provider the settings name, so action files work with Microsoft too. Access tokens are cached and refreshed a minute
before they expire. Another provider works with `token_url` (and `scope`); create the wrappers with its hosts.
Secrets never appear in log lines or error messages.

From Python:

```python
from je_mail_thunder import OAuth2Settings, SMTPStartTLSWrapper, oauth2_token_cache

settings = OAuth2Settings(user="you@contoso.com", provider="microsoft", client_id="...",
                          client_secret="...", refresh_token="...", tenant="contoso.onmicrosoft.com")
with SMTPStartTLSWrapper() as smtp:
    smtp.oauth2_login(settings.user, oauth2_token_cache.access_token(settings))
    smtp.create_message_and_send("Hello", {"Subject": "Hi", "From": settings.user, "To": "friend@example.com"})
```

### Authentication Objects

Each way of logging in is an `Authentication` object, so the code that connects does not care which one it is given:

| Class | Logs in with | Works for |
|---|---|---|
| `PasswordAuth(user, password)` | the account's password | SMTP, IMAP |
| `AppPasswordAuth(user, app_password)` | an app password (Google, Yahoo, iCloud); the spaces it is shown with are dropped | SMTP, IMAP |
| `OAuth2Auth(settings)` | an OAuth2 access token, as `Authorization: Bearer ...` | HTTP APIs |
| `XOAUTH2Auth(settings)` | the same token, as SASL `XOAUTH2` | SMTP, IMAP, HTTP APIs |

```python
from je_mail_thunder import AppPasswordAuth, OAuth2Settings, SMTPWrapper, XOAUTH2Auth, resolve_authentication

auth = AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop")
auth = XOAUTH2Auth(OAuth2Settings(user="you@gmail.com", client_id="...", client_secret="...", refresh_token="..."))
auth = resolve_authentication()   # what the config file or the environment holds, or None

with SMTPWrapper() as smtp:
    auth.login(smtp)              # the same call logs an IMAPWrapper in
```

`auth.login(client)` logs an SMTP or IMAP wrapper in, and `auth.authorization()` gives the value of an HTTP
`Authorization` header. A mechanism that cannot do one of them raises `MailThunderAuthenticationException`, which
`MailThunderOAuth2Exception` now subclasses. `settings` is an `OAuth2Settings`; the token comes from the shared token
cache and is refreshed a minute before it expires. `resolve_authentication()` prefers OAuth2 settings to a password,
as the wrappers do. Passwords and tokens never appear in a `repr`. Give one to `Mail(auth=...)` or
`MailAccount(auth=...)` to log in with it.

---

## Attachment Policy

An `AttachmentPolicy` says what a message may carry. `validate_attachments` checks a message's attachments against it
before anything is sent, and raises a structured exception at the first rule that is broken.

```python
from je_mail_thunder import Attachment, AttachmentPolicy, validate_attachments

policy = AttachmentPolicy(
    max_file_size=10 * 1024 * 1024,     # bytes one attachment may have
    max_total_size=20 * 1024 * 1024,    # bytes all attachments may have together
    max_count=5,
    allowed_extensions={"pdf", "csv", "html"},
    allowed_mime_types={"application/pdf", "text/*"},
)
attachments = [Attachment.from_path("report.pdf"), Attachment.from_path("results.csv")]
total_bytes = validate_attachments(attachments, policy)
```

Every limit is optional: `None`, the default, lifts it. Extensions are compared without case, with or without the
dot, and by the last extension (`report.pdf.exe` is an `.exe`). A MIME type may end in `/*`.
`DEFAULT_ATTACHMENT_POLICY` allows 25 MiB per attachment and per message, of any type.

The checks run in the order count → existence → size → extension → MIME type → total size:

| Exception | Raised when | Attributes |
|---|---|---|
| `AttachmentCountExceeded` | there are more attachments than `max_count` | `count`, `limit` |
| `AttachmentNotFound` | a file to attach does not exist | `path` |
| `AttachmentTooLarge` | one attachment is over `max_file_size` | `filename`, `size`, `limit` |
| `AttachmentTypeNotAllowed` | an extension or MIME type is not allowed | `filename`, `kind`, `value` |
| `TotalAttachmentSizeExceeded` | together they are over `max_total_size` | `size`, `limit` |

All of them subclass `MailThunderAttachmentException` (`je_mail_thunder.utils.exception.exceptions`). The type checks
read the file name, not the content: they stop the wrong file being sent by mistake, not a file renamed on purpose.

`Attachment.save(directory)` writes an attachment that arrived with a message. Its name is made safe first:
directory parts, `..`, control characters and the characters Windows refuses are removed, so the file cannot land
outside `directory`.

`Mail` applies its policy to every `send` and `create_draft`. The `SMTPWrapper` methods do not apply one; call
`validate_attachments` yourself before using them.

---

## Scripting Engine

MailThunder includes a JSON-based scripting engine that lets you automate email workflows without writing Python code.

### Action JSON Format

Action files use a list of commands. Each command is an array where the first element is the command name and the optional second element contains the arguments:

```json
{
  "mail_thunder": [
    ["command_name"],
    ["command_name", {"key": "value"}],
    ["command_name", ["arg1", "arg2"]]
  ]
}
```

- Use a **dict** `{}` as the second element for keyword arguments (`**kwargs`)
- Use a **list** `[]` as the second element for positional arguments (`*args`)
- Use only the command name (no second element) for commands with no arguments

### Available Script Commands

| Command | Description | Arguments |
|---------|-------------|-----------|
| `MT_smtp_later_init` | Initialize and log in to SMTP | None |
| `MT_smtp_create_message_and_send` | Create and send an email | `{"message_content": str, "message_setting_dict": dict}` |
| `MT_smtp_create_message_with_attach_and_send` | Create and send an email with attachment | `{"message_content": str, "message_setting_dict": dict, "attach_file": str, "use_html": bool}` |
| `MT_smtp_quit` | Disconnect from SMTP server (old name `smtp_quit` still accepted) | None |
| `MT_imap_later_init` | Initialize and log in to IMAP | None |
| `MT_imap_select_mailbox` | Select a mailbox | `{"mailbox": str, "readonly": bool}` (default: INBOX) |
| `MT_imap_search_mailbox` | Search and get mail details | `{"search_str": str, "charset": str}` |
| `MT_imap_mail_content_list` | Get all mail content as list | `{"search_str": str, "charset": str}` |
| `MT_imap_output_all_mail_as_file` | Export all emails to files | `{"search_str": str, "charset": str}` |
| `MT_imap_quit` | Disconnect from IMAP server | None |
| `MT_mail_send` | Send a message through the configured provider | `{"to": str or list, "subject": str, "text": str, "html": str, "cc": ..., "bcc": ..., "attachments": [paths], "sender": str, "reply_to": ..., "headers": dict}` |
| `MT_mail_create_draft` | Store a message as a draft | the `MT_mail_send` arguments, plus `"folder": str` |
| `MT_mail_get_messages` | Get the messages of a folder, newest first | `{"folder": str, "limit": int, "unread_only": bool, "query": str}` (default: INBOX, no limit) |
| `MT_mail_get_message` | Get one message by its id | `{"message_id": str, "folder": str}` |
| `MT_mail_delete_message` | Delete one message by its id | `{"message_id": str, "folder": str}` |
| `MT_mail_close` | Close the provider connections | None |
| `MT_set_mail_thunder_os_environ` | Set auth env vars | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | Get auth env vars | None |
| `MT_add_package_to_executor` | Load a Python package into executor | `["package_name"]` |

The `MT_mail_*` commands use the [Core Mail API](#core-mail-api) on `mail_instance`, a `Mail()` for the account of the
config file or the environment. They connect on first use and return JSON-ready values. Its attachment policy is set
from Python (`mail_instance.policy = AttachmentPolicy(...)`), never by an action, so an action file cannot loosen it.

**Example — Send a message and read the inbox through the Core Mail API:**

```json
{
  "mail_thunder": [
    ["MT_mail_send", {
      "to": "receiver@example.com",
      "subject": "Automated Email",
      "text": "Hello World!",
      "attachments": ["report.html"]
    }],
    ["MT_mail_get_messages", {"limit": 5, "unread_only": true}],
    ["MT_mail_close"]
  ]
}
```

**Example — Send an email via JSON script:**

```json
{
  "mail_thunder": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "Automated Email",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["MT_smtp_quit"]
  ]
}
```

**Example — Read and export all emails:**

```json
{
  "mail_thunder": [
    ["MT_imap_later_init"],
    ["MT_imap_select_mailbox"],
    ["MT_imap_output_all_mail_as_file"]
  ]
}
```

### Extending with Custom Commands

You can add your own functions to the scripting executor:

```python
from je_mail_thunder import add_command_to_executor

def my_custom_function(param1, param2):
    print(f"Custom: {param1}, {param2}")

add_command_to_executor({"my_command": my_custom_function})
```

Then use `"my_command"` in your JSON action files.

### Dynamic Package Loading

Load any installed Python package into the executor at runtime:

```json
{
  "mail_thunder": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

This loads all functions, builtins, and classes from the specified package, prefixed with `packagename_`.

**Package gate.** Because `MT_add_package_to_executor` can load `os` or `subprocess`, an action file or socket
client that names them could run anything. The host program decides what may load:

```python
from je_mail_thunder.utils.executor.action_executor import executor

executor.allow_packages("json")                # these, and their submodules
executor.set_allow_arbitrary_packages(False)   # refuse everything else before importing it
```

Neither switch is an action command, so an action file cannot open its own gate. A refused package is recorded
as an `ExecuteActionException` in that action's result. Until the host calls either switch, any package still
loads but raises a `DeprecationWarning`: a future release will refuse unlisted packages by default.

> **Warning:** Loading packages like `os` into the executor can be a security risk. Only load trusted packages and validate all inputs.

---

## Project Templates

MailThunder can scaffold a project with pre-built templates:

```python
from je_mail_thunder import create_project_dir

create_project_dir()  # Creates in current directory
# or
create_project_dir(project_path="/path/to/project", parent_name="MyMailProject")
```

This creates the following structure:

```
MyMailProject/
  keyword/
    keyword1.json      # SMTP send email template
    keyword2.json      # IMAP read and export template
    bad_keyword_1.json # Package loading example (security warning)
  executor/
    executor_one_file.py   # Execute a single action file
    executor_folder.py     # Execute all action files in a directory
    executor_bad_file.py   # Bad practice example
```

---

## Command-Line Interface

MailThunder provides a CLI via `python -m je_mail_thunder`:

```bash
# Execute a single JSON action file
python -m je_mail_thunder -e /path/to/action.json

# Execute all JSON action files in a directory
python -m je_mail_thunder -d /path/to/actions/

# Execute a JSON string directly
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["MT_smtp_quit"]]'

# Create a new project with templates
python -m je_mail_thunder -c /path/to/project
```

| Flag | Long Flag | Description |
|------|-----------|-------------|
| `-e` | `--execute_file` | Execute a single JSON action file |
| `-d` | `--execute_dir` | Execute all JSON action files in a directory |
| `-c` | `--create_project` | Create a project with templates |
| | `--execute_str` | Execute a JSON string directly |

---

## Socket Server

MailThunder includes a TCP socket server that accepts JSON commands remotely:

```python
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_mail_thunder_socket_server

server = start_mail_thunder_socket_server(host="localhost", port=9942)
# Server is now running in a background thread
```

**Sending commands to the server:**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9942))

# Send an action command
command = json.dumps([["MT_smtp_later_init"], ["MT_smtp_quit"]])
client.send(command.encode("utf-8"))

# Receive response
response = client.recv(8192).decode("utf-8")
print(response)

client.close()
```

Send `"quit_server"` to shut down the server.

---

## API Reference

### Mail

`Mail(provider=None, auth=None, account=None, policy=None, providers=None)`: the provider-agnostic API. A context
manager; nothing connects until the first call.

| Method | Description |
|--------|-------------|
| `send(message=None, **fields)` | Check and send a `MailMessage`, or the message built from `fields`; returns it |
| `create_draft(message=None, folder=None, **fields)` | Check a message and store it as a draft; returns its id, or `None` |
| `get_messages(folder="INBOX", limit=None, unread_only=False, query=None)` | Iterate over a folder's messages, newest first |
| `get_message(message_id, folder="INBOX")` | Return one message |
| `delete_message(message_id, folder="INBOX")` | Delete one message |
| `close()` | Close the connections; the next call connects again |

| Name | Description |
|------|-------------|
| `MailMessage(subject, to, cc, bcc, sender, reply_to, text, html, attachments, headers, message_id, date)` | The provider-independent message; `to_dict()` gives JSON-ready values |
| `MailAccount(provider="google", auth=None, servers=None)` / `MailServers(smtp_host, smtp_port, smtp_starttls, imap_host, drafts_folder)` | Whose mail, on which servers, with which login |
| `MailSender` / `MailStore` / `register_provider(name, factory)` | The provider interfaces and the registry; `SMTPProvider` and `IMAPProvider` implement them |
| `mail_instance` | The `Mail()` the `MT_mail_*` commands use |
| `legacy_message(...)` / `mail_from_wrappers(smtp=None, imap=None, policy=None)` | Bridges from the wrapper API |

### SMTPWrapper

Extends `smtplib.SMTP_SSL` (through `SMTPClientMixin`). Default host: `smtp.gmail.com`, default port: `465`.

| Method | Description |
|--------|-------------|
| `later_init()` | Log in using config file or environment variables (OAuth2 when configured) |
| `create_message(message_content, message_setting_dict, **kwargs)` | Create an `EmailMessage` object |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | Create a `MIMEMultipart` message with attachment |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | Create and immediately send an email |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | Create and send an email with attachment |
| `try_to_login_with_env_or_content()` | Attempt login from config or env vars (OAuth2 settings first, then user and password), returns `bool` |
| `oauth2_login(user, access_token)` | Log in with SASL `XOAUTH2`; raises `smtplib.SMTPAuthenticationError` when refused |
| `quit()` | Disconnect and close |

**Using a different SMTP provider:**

```python
from je_mail_thunder import SMTPStartTLSWrapper, SMTPWrapper

# Implicit TLS on another host
smtp = SMTPWrapper(host="smtp.example.com", port=465)
# STARTTLS, e.g. Microsoft 365 (smtp.office365.com:587 is the default)
smtp = SMTPStartTLSWrapper()
```

### SMTPStartTLSWrapper

Extends `smtplib.SMTP` with the same methods as `SMTPWrapper` (both mix in `SMTPClientMixin`). Default host:
`smtp.office365.com`, default port: `587`. It upgrades the connection with `STARTTLS` (certificate and host name
verified) before anything else is sent, and refuses a server that does not offer it: the connection is closed and
`smtplib.SMTPNotSupportedError` raised.

### IMAPWrapper

Extends `imaplib.IMAP4_SSL`. Default host: `imap.gmail.com`.

| Method | Description |
|--------|-------------|
| `later_init()` | Log in using config file or environment variables (OAuth2 when configured) |
| `select_mailbox(mailbox="INBOX", readonly=False)` | Select a mailbox, returns `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | Search and return raw mail details as list |
| `mail_content_list(search_str="ALL", charset=None)` | Return parsed mail content as list of dicts |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | Export all emails to files named by subject |
| `oauth2_login(user, access_token)` | Log in with SASL `XOAUTH2`; raises `imaplib.IMAP4.error` when refused |
| `quit()` | Close mailbox and logout |

**Mail content dict format:**

```python
{
    "SUBJECT": "Email subject",
    "FROM": "sender@example.com",
    "TO": "receiver@example.com",
    "BODY": "Email body content..."
}
```

### Executor Functions

| Function | Description |
|----------|-------------|
| `execute_action(action_list)` | Execute a list of action commands |
| `execute_files(execute_files_list)` | Execute multiple JSON action files |
| `add_command_to_executor(command_dict)` | Add custom functions to the executor |
| `read_action_json(file_path)` | Read a JSON action file |

### Utility Functions

| Function | Description |
|----------|-------------|
| `create_project_dir(project_path, parent_name)` | Create a project with templates |
| `set_mail_thunder_os_environ(mail_thunder_user, mail_thunder_user_password)` | Set authentication environment variables |
| `get_mail_thunder_os_environ()` | Get authentication environment variables |
| `read_output_content()` | Read `mail_thunder_content.json` from cwd |
| `write_output_content()` | Write content data to `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | Get all files in a directory as list |
| `OAuth2Settings(user, provider="google", client_id=None, client_secret=None, refresh_token=None, access_token=None, tenant="common", token_url=None, scope=None)` | OAuth2 login settings; `OAUTH2_PROVIDERS` holds the `google` and `microsoft` presets |
| `oauth2_token_cache.access_token(settings)` | A cached access token, refreshed when it is about to expire (`refresh_access_token(settings)` always asks the endpoint) |
| `resolve_oauth2_settings()` | The OAuth2 settings from the config file or the environment, or `None` |
| `xoauth2_string(user, access_token)` | The SASL `XOAUTH2` initial response |

---

## Project Structure

```
MailThunder/
  je_mail_thunder/
    __init__.py              # Public API exports
    __main__.py              # CLI entry point
    attachments/             # Attachment model, AttachmentPolicy and its validator
    auth/                    # Authentication: password, app password, OAuth2, XOAUTH2
    core/                    # Mail (the provider-agnostic API), MailMessage, MailAccount
    providers/               # MailSender / MailStore interfaces, SMTPProvider, IMAPProvider, registry
    smtp/
      smtp_wrapper.py        # SMTPClientMixin, SMTPWrapper, SMTPStartTLSWrapper
    imap/
      imap_wrapper.py        # IMAPWrapper class
    utils/
      exception/             # Custom exceptions and error tags
      executor/              # JSON scripting engine
      file_process/          # File utility functions
      json/                  # JSON file read/write
      json_format/           # JSON formatting
      lazy_instance/         # Lazy clients that connect on first use
      logging/               # Logger instance
      oauth2/                # OAuth2 settings, token refresh, XOAUTH2
      package_manager/       # Dynamic package loader
      project/               # Project template scaffolding
      save_mail_user_content/ # Auth config and env var handling
      socket_server/         # TCP socket server
  test/                      # Unit tests
  docs/                      # Sphinx documentation
```

---

## License

This project is licensed under the [MIT License](LICENSE).
