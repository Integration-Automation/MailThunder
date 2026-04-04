# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** is a lightweight and flexible email automation tool for Python. It wraps SMTP and IMAP4 protocols, provides a JSON-based scripting engine and project templates, and makes sending, receiving, and managing email content effortless.

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
- [Authentication](#authentication)
  - [JSON Config File](#json-config-file)
  - [Environment Variables](#environment-variables)
- [Scripting Engine](#scripting-engine)
  - [Action JSON Format](#action-json-format)
  - [Available Script Commands](#available-script-commands)
  - [Extending with Custom Commands](#extending-with-custom-commands)
  - [Dynamic Package Loading](#dynamic-package-loading)
- [Project Templates](#project-templates)
- [Command-Line Interface](#command-line-interface)
- [Socket Server](#socket-server)
- [API Reference](#api-reference)
  - [SMTPWrapper](#smtpwrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor Functions](#executor-functions)
  - [Utility Functions](#utility-functions)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

- **SMTP support** — Send emails via SSL with Gmail (default) or any SMTP provider
- **IMAP4 support** — Read, search, and export emails via IMAP4 SSL
- **Attachment handling** — Automatically detect MIME types for text, image, audio, and binary files
- **HTML email** — Send HTML-formatted emails with attachments
- **JSON scripting engine** — Automate email workflows using JSON action files
- **Project templates** — Scaffold projects with pre-built keyword and executor templates
- **Socket server** — Control MailThunder remotely via TCP socket commands
- **Package manager** — Dynamically load Python packages into the scripting executor
- **Environment variable auth** — Authenticate via config file or OS environment variables
- **Auto-export** — Export all mailbox emails to local files in one call
- **Context manager support** — Use `with` statement for both SMTP and IMAP connections
- **Logging** — Built-in logging for all operations

---

## Requirements

- Python 3.9 or later

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

## Authentication

MailThunder supports two authentication methods. It tries the JSON config file first, then falls back to environment variables.

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

---

## Scripting Engine

MailThunder includes a JSON-based scripting engine that lets you automate email workflows without writing Python code.

### Action JSON Format

Action files use a list of commands. Each command is an array where the first element is the command name and the optional second element contains the arguments:

```json
{
  "auto_control": [
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
| `smtp_quit` | Disconnect from SMTP server | None |
| `MT_imap_later_init` | Initialize and log in to IMAP | None |
| `MT_imap_select_mailbox` | Select a mailbox | `{"mailbox": str, "readonly": bool}` (default: INBOX) |
| `MT_imap_search_mailbox` | Search and get mail details | `{"search_str": str, "charset": str}` |
| `MT_imap_mail_content_list` | Get all mail content as list | `{"search_str": str, "charset": str}` |
| `MT_imap_output_all_mail_as_file` | Export all emails to files | `{"search_str": str, "charset": str}` |
| `MT_imap_quit` | Disconnect from IMAP server | None |
| `MT_set_mail_thunder_os_environ` | Set auth env vars | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | Get auth env vars | None |
| `MT_add_package_to_executor` | Load a Python package into executor | `["package_name"]` |

**Example — Send an email via JSON script:**

```json
{
  "auto_control": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "Automated Email",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["smtp_quit"]
  ]
}
```

**Example — Read and export all emails:**

```json
{
  "auto_control": [
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
  "auto_control": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

This loads all functions, builtins, and classes from the specified package, prefixed with `packagename_`.

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
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["smtp_quit"]]'

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
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_autocontrol_socket_server

server = start_autocontrol_socket_server(host="localhost", port=9944)
# Server is now running in a background thread
```

**Sending commands to the server:**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9944))

# Send an action command
command = json.dumps([["MT_smtp_later_init"], ["smtp_quit"]])
client.send(command.encode("utf-8"))

# Receive response
response = client.recv(8192).decode("utf-8")
print(response)

client.close()
```

Send `"quit_server"` to shut down the server.

---

## API Reference

### SMTPWrapper

Extends `smtplib.SMTP_SSL`. Default host: `smtp.gmail.com`, default port: `465`.

| Method | Description |
|--------|-------------|
| `later_init()` | Log in using config file or environment variables |
| `create_message(message_content, message_setting_dict, **kwargs)` | Create an `EmailMessage` object |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | Create a `MIMEMultipart` message with attachment |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | Create and immediately send an email |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | Create and send an email with attachment |
| `try_to_login_with_env_or_content()` | Attempt login from config or env vars, returns `bool` |
| `quit()` | Disconnect and close |

**Using a different SMTP provider:**

```python
from je_mail_thunder import SMTPWrapper

# Example: Outlook
smtp = SMTPWrapper(host="smtp.office365.com", port=587)
```

### IMAPWrapper

Extends `imaplib.IMAP4_SSL`. Default host: `imap.gmail.com`.

| Method | Description |
|--------|-------------|
| `later_init()` | Log in using config file or environment variables |
| `select_mailbox(mailbox="INBOX", readonly=False)` | Select a mailbox, returns `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | Search and return raw mail details as list |
| `mail_content_list(search_str="ALL", charset=None)` | Return parsed mail content as list of dicts |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | Export all emails to files named by subject |
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
| `set_mail_thunder_os_environ(user, password)` | Set authentication environment variables |
| `get_mail_thunder_os_environ()` | Get authentication environment variables |
| `read_output_content()` | Read `mail_thunder_content.json` from cwd |
| `write_output_content()` | Write content data to `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | Get all files in a directory as list |

---

## Project Structure

```
MailThunder/
  je_mail_thunder/
    __init__.py              # Public API exports
    __main__.py              # CLI entry point
    smtp/
      smtp_wrapper.py        # SMTPWrapper class
    imap/
      imap_wrapper.py        # IMAPWrapper class
    utils/
      exception/             # Custom exceptions and error tags
      executor/              # JSON scripting engine
      file_process/          # File utility functions
      json/                  # JSON file read/write
      json_format/           # JSON formatting
      logging/               # Logger instance
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
