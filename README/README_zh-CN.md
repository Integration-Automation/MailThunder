# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** 是一款轻量且灵活的 Python 电子邮件自动化工具。它封装了 SMTP 和 IMAP4 协议，提供 JSON 脚本引擎与项目模板功能，让发信、收信与管理邮件内容变得轻松简单。

**[English](../README.md)** | **[繁體中文](README_zh-TW.md)**

---

## 目录

- [功能特色](#功能特色)
- [系统需求](#系统需求)
- [安装](#安装)
- [快速开始](#快速开始)
  - [配置](#配置)
  - [发送邮件 (SMTP)](#发送邮件-smtp)
  - [发送带附件的邮件](#发送带附件的邮件)
  - [读取邮件 (IMAP)](#读取邮件-imap)
  - [导出所有邮件为文件](#导出所有邮件为文件)
- [身份验证](#身份验证)
  - [JSON 配置文件](#json-配置文件)
  - [环境变量](#环境变量)
- [脚本引擎](#脚本引擎)
  - [Action JSON 格式](#action-json-格式)
  - [可用的脚本指令](#可用的脚本指令)
  - [扩展自定义指令](#扩展自定义指令)
  - [动态加载包](#动态加载包)
- [项目模板](#项目模板)
- [命令行界面](#命令行界面)
- [Socket 服务器](#socket-服务器)
- [API 参考](#api-参考)
  - [SMTPWrapper](#smtpwrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函数](#executor-函数)
  - [工具函数](#工具函数)
- [项目结构](#项目结构)
- [许可证](#许可证)

---

## 功能特色

- **SMTP 支持** — 通过 SSL 发送邮件，默认使用 Gmail，也可自定义其他 SMTP 服务
- **IMAP4 支持** — 通过 IMAP4 SSL 读取、搜索和导出邮件
- **附件处理** — 自动检测文本、图片、音频和二进制文件的 MIME 类型
- **HTML 邮件** — 支持发送 HTML 格式的邮件与附件
- **JSON 脚本引擎** — 使用 JSON 动作文件自动化邮件工作流程
- **项目模板** — 快速创建包含预设关键字和执行器模板的项目
- **Socket 服务器** — 通过 TCP Socket 远程控制 MailThunder
- **包管理器** — 动态加载 Python 包至脚本执行器
- **环境变量验证** — 支持配置文件或操作系统环境变量进行身份验证
- **自动导出** — 一行指令即可将邮箱所有邮件导出为本地文件
- **Context Manager 支持** — SMTP 和 IMAP 连接均可使用 `with` 语法
- **日志记录** — 内置所有操作的日志记录

---

## 系统需求

- Python 3.9 或更新版本

---

## 安装

**稳定版：**

```bash
pip install je_mail_thunder
```

**开发版：**

```bash
pip install je_mail_thunder_dev
```

---

## 快速开始

### 配置

使用 MailThunder 之前，需要先配置身份验证。在当前工作目录下创建一个名为 `mail_thunder_content.json` 的文件：

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

> **重要提示：** 若使用 Gmail，必须使用[应用专用密码](https://support.google.com/accounts/answer/185833)，而非普通的 Google 账户密码。同时需要在 Gmail 设置中[启用 IMAP](https://support.google.com/mail/answer/7126229?hl=zh-Hans)。

### 发送邮件 (SMTP)

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()  # 使用配置文件或环境变量登录
    smtp.create_message_and_send(
        message_content="来自 MailThunder 的问候！",
        message_setting_dict={
            "Subject": "测试邮件",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        }
    )
```

### 发送带附件的邮件

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()
    smtp.create_message_with_attach_and_send(
        message_content="请查看附件。",
        message_setting_dict={
            "Subject": "带附件的邮件",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        },
        attach_file="/path/to/file.pdf",
        use_html=False  # 若 message_content 为 HTML 则设为 True
    )
```

### 读取邮件 (IMAP)

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()  # 登录
    imap.select_mailbox("INBOX")
    emails = imap.mail_content_list()
    for mail in emails:
        print(f"主题: {mail['SUBJECT']}")
        print(f"发件人: {mail['FROM']}")
        print(f"内容: {mail['BODY'][:100]}...")
```

### 导出所有邮件为文件

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()
    imap.select_mailbox("INBOX")
    imap.output_all_mail_as_file()  # 以邮件主题为文件名保存每封邮件
```

---

## 身份验证

MailThunder 支持两种身份验证方式。它会先尝试 JSON 配置文件，若找不到则回退至环境变量。

### JSON 配置文件

在当前工作目录下放置 `mail_thunder_content.json`：

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

### 环境变量

在运行脚本前设置以下环境变量：

```python
from je_mail_thunder import set_mail_thunder_os_environ

set_mail_thunder_os_environ(
    mail_thunder_user="your_email@gmail.com",
    mail_thunder_user_password="your_app_password"
)
```

或在 Shell 中设置：

```bash
export mail_thunder_user="your_email@gmail.com"
export mail_thunder_user_password="your_app_password"
```

---

## 脚本引擎

MailThunder 内置 JSON 脚本引擎，让你无需编写 Python 代码即可自动化邮件工作流程。

### Action JSON 格式

动作文件使用指令列表格式。每个指令为一个数组，第一个元素为指令名称，可选的第二个元素为参数：

```json
{
  "auto_control": [
    ["指令名称"],
    ["指令名称", {"key": "value"}],
    ["指令名称", ["arg1", "arg2"]]
  ]
}
```

- 使用 **dict** `{}` 作为第二个元素传递关键字参数（`**kwargs`）
- 使用 **list** `[]` 作为第二个元素传递位置参数（`*args`）
- 只写指令名称（不含第二个元素）表示无参数指令

### 可用的脚本指令

| 指令 | 说明 | 参数 |
|------|------|------|
| `MT_smtp_later_init` | 初始化并登录 SMTP | 无 |
| `MT_smtp_create_message_and_send` | 创建并发送邮件 | `{"message_content": str, "message_setting_dict": dict}` |
| `MT_smtp_create_message_with_attach_and_send` | 创建并发送带附件的邮件 | `{"message_content": str, "message_setting_dict": dict, "attach_file": str, "use_html": bool}` |
| `smtp_quit` | 断开 SMTP 连接 | 无 |
| `MT_imap_later_init` | 初始化并登录 IMAP | 无 |
| `MT_imap_select_mailbox` | 选择邮箱 | `{"mailbox": str, "readonly": bool}`（默认：INBOX）|
| `MT_imap_search_mailbox` | 搜索并获取邮件详细信息 | `{"search_str": str, "charset": str}` |
| `MT_imap_mail_content_list` | 获取所有邮件内容列表 | `{"search_str": str, "charset": str}` |
| `MT_imap_output_all_mail_as_file` | 导出所有邮件为文件 | `{"search_str": str, "charset": str}` |
| `MT_imap_quit` | 断开 IMAP 连接 | 无 |
| `MT_set_mail_thunder_os_environ` | 设置验证环境变量 | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | 获取验证环境变量 | 无 |
| `MT_add_package_to_executor` | 加载 Python 包至执行器 | `["包名称"]` |

**示例 — 通过 JSON 脚本发送邮件：**

```json
{
  "auto_control": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "自动化邮件",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["smtp_quit"]
  ]
}
```

**示例 — 读取并导出所有邮件：**

```json
{
  "auto_control": [
    ["MT_imap_later_init"],
    ["MT_imap_select_mailbox"],
    ["MT_imap_output_all_mail_as_file"]
  ]
}
```

### 扩展自定义指令

你可以将自己的函数加入脚本执行器：

```python
from je_mail_thunder import add_command_to_executor

def my_custom_function(param1, param2):
    print(f"自定义指令: {param1}, {param2}")

add_command_to_executor({"my_command": my_custom_function})
```

之后即可在 JSON 动作文件中使用 `"my_command"`。

### 动态加载包

在运行时动态加载任何已安装的 Python 包至执行器：

```json
{
  "auto_control": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

这会加载指定包的所有函数、内置功能和类，并以 `包名称_` 为前缀。

> **警告：** 将 `os` 等包加载至执行器可能存在安全风险。请仅加载可信任的包并验证所有输入。

---

## 项目模板

MailThunder 可以快速创建包含预设模板的项目：

```python
from je_mail_thunder import create_project_dir

create_project_dir()  # 在当前目录创建
# 或
create_project_dir(project_path="/path/to/project", parent_name="MyMailProject")
```

创建的目录结构如下：

```
MyMailProject/
  keyword/
    keyword1.json      # SMTP 发送邮件模板
    keyword2.json      # IMAP 读取并导出模板
    bad_keyword_1.json # 包加载示例（安全性警告）
  executor/
    executor_one_file.py   # 执行单一动作文件
    executor_folder.py     # 执行目录内所有动作文件
    executor_bad_file.py   # 不良实践示例
```

---

## 命令行界面

MailThunder 通过 `python -m je_mail_thunder` 提供命令行界面：

```bash
# 执行单一 JSON 动作文件
python -m je_mail_thunder -e /path/to/action.json

# 执行目录内所有 JSON 动作文件
python -m je_mail_thunder -d /path/to/actions/

# 直接执行 JSON 字符串
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["smtp_quit"]]'

# 创建包含模板的新项目
python -m je_mail_thunder -c /path/to/project
```

| 标志 | 完整标志 | 说明 |
|------|----------|------|
| `-e` | `--execute_file` | 执行单一 JSON 动作文件 |
| `-d` | `--execute_dir` | 执行目录内所有 JSON 动作文件 |
| `-c` | `--create_project` | 创建包含模板的项目 |
| | `--execute_str` | 直接执行 JSON 字符串 |

---

## Socket 服务器

MailThunder 内置 TCP Socket 服务器，可接收远程 JSON 指令：

```python
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_autocontrol_socket_server

server = start_autocontrol_socket_server(host="localhost", port=9944)
# 服务器现在在后台线程中运行
```

**向服务器发送指令：**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9944))

# 发送动作指令
command = json.dumps([["MT_smtp_later_init"], ["smtp_quit"]])
client.send(command.encode("utf-8"))

# 接收响应
response = client.recv(8192).decode("utf-8")
print(response)

client.close()
```

发送 `"quit_server"` 可关闭服务器。

---

## API 参考

### SMTPWrapper

继承自 `smtplib.SMTP_SSL`。默认主机：`smtp.gmail.com`，默认端口：`465`。

| 方法 | 说明 |
|------|------|
| `later_init()` | 使用配置文件或环境变量登录 |
| `create_message(message_content, message_setting_dict, **kwargs)` | 创建 `EmailMessage` 对象 |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | 创建带附件的 `MIMEMultipart` 消息 |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | 创建并立即发送邮件 |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | 创建并发送带附件的邮件 |
| `try_to_login_with_env_or_content()` | 尝试从配置文件或环境变量登录，返回 `bool` |
| `quit()` | 断开连接并关闭 |

**使用其他 SMTP 服务商：**

```python
from je_mail_thunder import SMTPWrapper

# 示例：Outlook
smtp = SMTPWrapper(host="smtp.office365.com", port=587)
```

### IMAPWrapper

继承自 `imaplib.IMAP4_SSL`。默认主机：`imap.gmail.com`。

| 方法 | 说明 |
|------|------|
| `later_init()` | 使用配置文件或环境变量登录 |
| `select_mailbox(mailbox="INBOX", readonly=False)` | 选择邮箱，返回 `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | 搜索并返回原始邮件详细信息列表 |
| `mail_content_list(search_str="ALL", charset=None)` | 返回已解析的邮件内容字典列表 |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主题为文件名导出所有邮件 |
| `quit()` | 关闭邮箱并登出 |

**邮件内容字典格式：**

```python
{
    "SUBJECT": "邮件主题",
    "FROM": "sender@example.com",
    "TO": "receiver@example.com",
    "BODY": "邮件内容..."
}
```

### Executor 函数

| 函数 | 说明 |
|------|------|
| `execute_action(action_list)` | 执行动作指令列表 |
| `execute_files(execute_files_list)` | 执行多个 JSON 动作文件 |
| `add_command_to_executor(command_dict)` | 将自定义函数加入执行器 |
| `read_action_json(file_path)` | 读取 JSON 动作文件 |

### 工具函数

| 函数 | 说明 |
|------|------|
| `create_project_dir(project_path, parent_name)` | 创建包含模板的项目 |
| `set_mail_thunder_os_environ(user, password)` | 设置验证环境变量 |
| `get_mail_thunder_os_environ()` | 获取验证环境变量 |
| `read_output_content()` | 从当前工作目录读取 `mail_thunder_content.json` |
| `write_output_content()` | 将内容数据写入 `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | 获取目录内所有文件列表 |

---

## 项目结构

```
MailThunder/
  je_mail_thunder/
    __init__.py              # 公开 API 导出
    __main__.py              # CLI 入口点
    smtp/
      smtp_wrapper.py        # SMTPWrapper 类
    imap/
      imap_wrapper.py        # IMAPWrapper 类
    utils/
      exception/             # 自定义异常与错误标签
      executor/              # JSON 脚本引擎
      file_process/          # 文件工具函数
      json/                  # JSON 文件读写
      json_format/           # JSON 格式化
      logging/               # 日志实例
      package_manager/       # 动态包加载器
      project/               # 项目模板创建
      save_mail_user_content/ # 验证配置与环境变量处理
      socket_server/         # TCP Socket 服务器
  test/                      # 单元测试
  docs/                      # Sphinx 文档
```

---

## 许可证

本项目采用 [MIT 许可证](../LICENSE)。

Copyright (c) 2021 JE-Chen
