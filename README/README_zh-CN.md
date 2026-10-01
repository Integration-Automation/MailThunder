# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
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
  - [OAuth2（Google 与 Microsoft）](#oauth2google-与-microsoft)
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
  - [SMTPStartTLSWrapper](#smtpstarttlswrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函数](#executor-函数)
  - [工具函数](#工具函数)
- [项目结构](#项目结构)
- [许可证](#许可证)

---

## 功能特色

- **SMTP 支持** — 通过隐式 TLS 发送邮件，默认使用 Gmail，也可自定义其他 SMTP 服务；或通过 STARTTLS（Microsoft 365）
- **IMAP4 支持** — 通过 IMAP4 SSL 读取、搜索和导出邮件
- **附件处理** — 自动检测文本、图片、音频和二进制文件的 MIME 类型
- **HTML 邮件** — 支持发送 HTML 格式的邮件与附件
- **JSON 脚本引擎** — 使用 JSON 动作文件自动化邮件工作流程
- **项目模板** — 快速创建包含预设关键字和执行器模板的项目
- **Socket 服务器** — 通过 TCP Socket 远程控制 MailThunder
- **包管理器** — 动态加载 Python 包至脚本执行器
- **环境变量验证** — 支持配置文件或操作系统环境变量进行身份验证
- **OAuth2 登录** — Gmail 与 Microsoft 365 的 SASL `XOAUTH2`，以标准库交换 refresh token 并缓存访问令牌
- **自动导出** — 一行指令即可将邮箱所有邮件导出为本地文件
- **Context Manager 支持** — SMTP 和 IMAP 连接均可使用 `with` 语法
- **日志记录** — 内置所有操作的日志记录

---

## 系统需求

- Python 3.10 或更新版本
- `je_action_core`，安装时会一并装上：MailThunder 与 APITestka、LoadDensity、FileAutomation 共用的 action 执行器（它只用 Python 标准库）

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

MailThunder 以密码或 OAuth2 登录。它会先读 JSON 配置文件，再读环境变量；有 OAuth2 配置时，以 OAuth2 取代密码。

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

### OAuth2（Google 与 Microsoft）

Google 与 Microsoft 都在淘汰邮件的密码登录。使用 OAuth2 时，MailThunder 在服务商的令牌端点以 refresh token 换取短效的
访问令牌（只用标准库，且必须是 `https`），再以 SASL `XOAUTH2` 登录。client ID、client secret 与 refresh token
要先通过服务商的授权流程获取一次（Google Cloud 的 OAuth 客户端，或 Microsoft Entra 的应用注册）；MailThunder
不执行那个流程。

在 `mail_thunder_content.json` 中：

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

或用环境变量：`mail_thunder_user` 加上 `mail_thunder_oauth2_provider`、`mail_thunder_oauth2_client_id`、`mail_thunder_oauth2_client_secret`、`mail_thunder_oauth2_refresh_token`；可选 `mail_thunder_oauth2_tenant`、`mail_thunder_oauth2_scope`、`mail_thunder_oauth2_token_url`、`mail_thunder_oauth2_access_token`（直接使用给定的令牌）。

| 服务商 | SMTP | IMAP | 请求的范围 |
|---|---|---|---|
| `google`（默认） | `smtp.gmail.com:465`，隐式 TLS（`SMTPWrapper`） | `imap.gmail.com` | `https://mail.google.com/` |
| `microsoft` | `smtp.office365.com:587`，STARTTLS（`SMTPStartTLSWrapper`） | `outlook.office365.com` | `https://outlook.office.com/` 上的 `SMTP.Send`、`IMAP.AccessAsUser.All`，以及 `offline_access` |

`smtp_instance` 与 `imap_instance`（以及 `MT_smtp_*`／`MT_imap_*` 指令）会连到配置所指服务商的服务器，所以动作文件也能
用 Microsoft。访问令牌会缓存，并在到期前一分钟刷新。其他服务商可用 `token_url`（与 `scope`），再以它的主机自行创建
wrapper。密钥不会出现在日志或错误消息里。

在 Python 中：

```python
from je_mail_thunder import OAuth2Settings, SMTPStartTLSWrapper, oauth2_token_cache

settings = OAuth2Settings(user="you@contoso.com", provider="microsoft", client_id="...",
                          client_secret="...", refresh_token="...", tenant="contoso.onmicrosoft.com")
with SMTPStartTLSWrapper() as smtp:
    smtp.oauth2_login(settings.user, oauth2_token_cache.access_token(settings))
    smtp.create_message_and_send("Hello", {"Subject": "Hi", "From": settings.user, "To": "friend@example.com"})
```

---

## 脚本引擎

MailThunder 内置 JSON 脚本引擎，让你无需编写 Python 代码即可自动化邮件工作流程。

### Action JSON 格式

动作文件使用指令列表格式。每个指令为一个数组，第一个元素为指令名称，可选的第二个元素为参数：

```json
{
  "mail_thunder": [
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
| `MT_smtp_quit` | 断开 SMTP 连接（旧名 `smtp_quit` 仍可用） | 无 |
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
  "mail_thunder": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "自动化邮件",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["MT_smtp_quit"]
  ]
}
```

**示例 — 读取并导出所有邮件：**

```json
{
  "mail_thunder": [
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
  "mail_thunder": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

这会加载指定包的所有函数、内置功能和类，并以 `包名称_` 为前缀。

**包闸门。** `MT_add_package_to_executor` 能加载 `os` 或 `subprocess`，所以只要 action 文件或 socket 客户端写得出
这些名字，就能执行任何东西。哪些包可以加载，由宿主程序决定：

```python
from je_mail_thunder.utils.executor.action_executor import executor

executor.allow_packages("json")                # 这些包与其子模块
executor.set_allow_arbitrary_packages(False)   # 其他包在导入前就拒绝
```

这两个开关都不是 action 命令，所以 action 文件不能自己打开闸门。被拒绝的包会以 `ExecuteActionException`
记录在该动作的结果里。宿主程序调用任一个开关之前，任何包仍会加载，但会发出 `DeprecationWarning`：之后的版本会
默认拒绝清单以外的包。

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
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["MT_smtp_quit"]]'

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
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_mail_thunder_socket_server

server = start_mail_thunder_socket_server(host="localhost", port=9942)
# 服务器现在在后台线程中运行
```

**向服务器发送指令：**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9942))

# 发送动作指令
command = json.dumps([["MT_smtp_later_init"], ["MT_smtp_quit"]])
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

继承自 `smtplib.SMTP_SSL`（经由 `SMTPClientMixin`）。默认主机：`smtp.gmail.com`，默认端口：`465`。

| 方法 | 说明 |
|------|------|
| `later_init()` | 使用配置文件或环境变量登录（有 OAuth2 配置时用 OAuth2） |
| `create_message(message_content, message_setting_dict, **kwargs)` | 创建 `EmailMessage` 对象 |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | 创建带附件的 `MIMEMultipart` 消息 |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | 创建并立即发送邮件 |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | 创建并发送带附件的邮件 |
| `try_to_login_with_env_or_content()` | 尝试从配置文件或环境变量登录（先 OAuth2 配置，再账号密码），返回 `bool` |
| `oauth2_login(user, access_token)` | 以 SASL `XOAUTH2` 登录；被拒时抛出 `smtplib.SMTPAuthenticationError` |
| `quit()` | 断开连接并关闭 |

**使用其他 SMTP 服务商：**

```python
from je_mail_thunder import SMTPStartTLSWrapper, SMTPWrapper

# 其他主机的隐式 TLS
smtp = SMTPWrapper(host="smtp.example.com", port=465)
# STARTTLS，例如 Microsoft 365（默认即 smtp.office365.com:587）
smtp = SMTPStartTLSWrapper()
```

### SMTPStartTLSWrapper

继承自 `smtplib.SMTP`，方法与 `SMTPWrapper` 相同（两者都混入 `SMTPClientMixin`）。默认主机：`smtp.office365.com`，
默认端口：`587`。它在发送任何其他内容前先以 `STARTTLS` 升级连接（验证证书与主机名），并拒绝不提供 `STARTTLS` 的
服务器：关闭连接并抛出 `smtplib.SMTPNotSupportedError`。

### IMAPWrapper

继承自 `imaplib.IMAP4_SSL`。默认主机：`imap.gmail.com`。

| 方法 | 说明 |
|------|------|
| `later_init()` | 使用配置文件或环境变量登录（有 OAuth2 配置时用 OAuth2） |
| `select_mailbox(mailbox="INBOX", readonly=False)` | 选择邮箱，返回 `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | 搜索并返回原始邮件详细信息列表 |
| `mail_content_list(search_str="ALL", charset=None)` | 返回已解析的邮件内容字典列表 |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主题为文件名导出所有邮件 |
| `oauth2_login(user, access_token)` | 以 SASL `XOAUTH2` 登录；被拒时抛出 `imaplib.IMAP4.error` |
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
| `set_mail_thunder_os_environ(mail_thunder_user, mail_thunder_user_password)` | 设置验证环境变量 |
| `get_mail_thunder_os_environ()` | 获取验证环境变量 |
| `read_output_content()` | 从当前工作目录读取 `mail_thunder_content.json` |
| `write_output_content()` | 将内容数据写入 `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | 获取目录内所有文件列表 |
| `OAuth2Settings(user, provider="google", client_id=None, client_secret=None, refresh_token=None, access_token=None, tenant="common", token_url=None, scope=None)` | OAuth2 登录配置；`OAUTH2_PROVIDERS` 有 `google` 与 `microsoft` 预设 |
| `oauth2_token_cache.access_token(settings)` | 缓存的访问令牌，快到期时刷新（`refresh_access_token(settings)` 每次都向端点请求） |
| `resolve_oauth2_settings()` | 从配置文件或环境变量获取 OAuth2 配置，没有则为 `None` |
| `xoauth2_string(user, access_token)` | SASL `XOAUTH2` 的初始响应 |

---

## 项目结构

```
MailThunder/
  je_mail_thunder/
    __init__.py              # 公开 API 导出
    __main__.py              # CLI 入口点
    smtp/
      smtp_wrapper.py        # SMTPClientMixin、SMTPWrapper、SMTPStartTLSWrapper
    imap/
      imap_wrapper.py        # IMAPWrapper 类
    utils/
      exception/             # 自定义异常与错误标签
      executor/              # JSON 脚本引擎
      file_process/          # 文件工具函数
      json/                  # JSON 文件读写
      json_format/           # JSON 格式化
      lazy_instance/         # 首次使用时才连接的惰性客户端
      logging/               # 日志实例
      oauth2/                # OAuth2 配置、令牌刷新、XOAUTH2
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
