# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** 是一款轻量且灵活的 Python 电子邮件自动化工具。它与提供商无关的 `Mail` API 不论背后是哪一家提供商，都以同样的方式发信与读信；它封装了 SMTP 和 IMAP4 协议，提供 JSON 脚本引擎与项目模板功能，让发信、收信与管理邮件内容变得轻松简单。

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
- [核心邮件 API](#核心邮件-api)
  - [发送邮件 (Mail)](#发送邮件-mail)
  - [读取、草稿与删除](#读取草稿与删除)
  - [账号与提供商](#账号与提供商)
  - [错误](#错误)
  - [从 Wrapper 迁移](#从-wrapper-迁移)
- [身份验证](#身份验证)
  - [JSON 配置文件](#json-配置文件)
  - [环境变量](#环境变量)
  - [OAuth2（Google 与 Microsoft）](#oauth2google-与-microsoft)
  - [验证对象](#验证对象)
- [附件策略](#附件策略)
- [邮件模板](#邮件模板)
- [邮件事件与触发器](#邮件事件与触发器)
- [Microsoft Graph](#microsoft-graph)
- [监控](#监控)
- [项目邮件层](#项目邮件层)
- [MailThunder Studio](#mailthunder-studio)
- [脚本引擎](#脚本引擎)
  - [Action JSON 格式](#action-json-格式)
  - [可用的脚本指令](#可用的脚本指令)
  - [扩展自定义指令](#扩展自定义指令)
  - [动态加载包](#动态加载包)
- [项目模板](#项目模板)
- [命令行界面](#命令行界面)
- [Socket 服务器](#socket-服务器)
- [API 参考](#api-参考)
  - [Mail](#mail)
  - [SMTPWrapper](#smtpwrapper)
  - [SMTPStartTLSWrapper](#smtpstarttlswrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函数](#executor-函数)
  - [工具函数](#工具函数)
- [项目结构](#项目结构)
- [许可证](#许可证)

---

## 功能特色

- **与提供商无关的 `Mail` API** — 一个对象就能发送、读取、创建草稿与删除邮件；背后是可以接上新后端的提供商接口（目前为 SMTP 与 IMAP）
- **邮件模板** — 主题、纯文本与 HTML 模板，支持 Jinja2 风格的 `{{ }}`、`{% if %}` 与 `{% for %}`，以标准库实现：`mail.send(template=..., context=...)`
- **邮件事件与触发器** — `mail.on("message_received", handler, filter={...})` 提供与提供商无关的事件，`mail.watch()` 以轮询或 IMAP IDLE 监看新邮件
- **Microsoft Graph 提供商** — 以 OAuth2 通过 Graph API 发送、创建草稿、读取与删除 Microsoft 365 邮件，并提供轮询与 webhook 触发器
- **监控** — 只能附加的审计日志、每个提供商的健康报告，以及带签章的对外 webhook，全部由邮件事件驱动
- **更多提供商** — Yahoo、iCloud、Zoho 与 Fastmail 的默认值，以及把邮件留在磁盘上、供试跑使用的 `file` 提供商
- **项目邮件层** — 项目把提供商、策略、模板与触发器放在 `mail/`，`project_mail()` 就能给程序一个设置好的 `Mail`
- **MailThunder Studio** — 本机页面（`python -m je_mail_thunder.studio`），可查看帐号、模板、触发器、策略、项目邮件层与日志，由标准库提供服务
- **SMTP 支持** — 通过隐式 TLS 发送邮件，默认使用 Gmail，也可自定义其他 SMTP 服务；或通过 STARTTLS（Microsoft 365）
- **IMAP4 支持** — 通过 IMAP4 SSL 读取、搜索和导出邮件
- **附件处理** — 自动检测文本、图片、音频和二进制文件的 MIME 类型
- **附件策略** — 发送前检查附件的数量、大小、扩展名与 MIME 类型，每条规则都有对应的结构化异常
- **HTML 邮件** — 支持发送 HTML 格式的邮件与附件
- **JSON 脚本引擎** — 使用 JSON 动作文件自动化邮件工作流程
- **项目模板** — 快速创建包含预设关键字和执行器模板的项目
- **Socket 服务器** — 通过 TCP Socket 远程控制 MailThunder
- **包管理器** — 动态加载 Python 包至脚本执行器
- **环境变量验证** — 支持配置文件或操作系统环境变量进行身份验证
- **OAuth2 登录** — Gmail 与 Microsoft 365 的 SASL `XOAUTH2`，以标准库交换 refresh token 并缓存访问令牌
- **验证对象** — `PasswordAuth`、`AppPasswordAuth`、`OAuth2Auth` 与 `XOAUTH2Auth`，共用同一个 `Authentication` 接口
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

`je_mail_thunder_dev` 跟随 `dev` 分支：每次推送到 `dev` 通过测试、并且包内容有变化时，CI 就会发布一个新版本。

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

## 核心邮件 API

`Mail` 是与提供商无关的 API：不论账号用的是哪一家提供商，都用同一组调用来发送、读取、创建草稿与删除邮件。
它使用[身份验证](#身份验证)一节说明的认证信息，在第一次使用时才连接，之后的调用沿用同一条连接；
发生错误时会抛出异常，而不是只写入日志。

### 发送邮件 (Mail)

```python
from je_mail_thunder import Mail

with Mail() as mail:                       # Gmail，或 OAuth2 配置指定的提供商
    mail.send(
        to="receiver@example.com",         # 一个地址、以逗号分隔的多个地址，或列表
        cc=["team@example.com"],
        subject="Nightly report",
        text="42 passed, 0 failed.",
        html="<b>42</b> passed, 0 failed.",
        attachments=["report.html"],
    )
```

`text` 与 `html` 都给时，邮件会同时携带两种版本。发件人默认为账号的用户，也可以用 `sender=` 指定；
另外接受 `bcc`、`reply_to` 与 `headers`。在任何数据发到服务器之前，邮件会先经过检查：至少一位收件人、
地址有效、主题与标头的值为单行（因此无法通过某个值夹带第二个标头），以及附件是否符合[附件策略](#附件策略)
（`Mail(policy=...)`；默认为 25 MiB、任何类型）。

### 读取、草稿与删除

```python
from je_mail_thunder import Mail

with Mail() as mail:
    for message in mail.get_messages(folder="INBOX", limit=10, unread_only=True):
        print(message.message_id, message.sender, message.subject)
        for attachment in message.attachments:
            attachment.save("downloads")    # 写入的文件名不会离开该目录

    message = mail.get_message("4321")      # 使用 get_messages 给的 message_id
    mail.create_draft(to="receiver@example.com", subject="Later", text="...")
    mail.delete_message("4321")
```

`get_messages` 返回迭代器，最新的邮件在前：邮件一封一封取回，不会把整个大邮箱放进内存，而且读取不会把邮件
标成已读。`query=` 接受提供商自己的搜索语法（IMAP `SEARCH` 条件，例如 `'FROM "ci@example.com" SINCE 1-Oct-2026'`）。
每封邮件都是 `MailMessage`，有 `subject`、`sender`、`to`、`cc`、`reply_to`、`date`、`text`、`html`、`attachments`、
`headers` 与 `message_id`。

### 账号与提供商

```python
from je_mail_thunder import AppPasswordAuth, Mail, MailAccount, MailServers

Mail(provider="microsoft")                  # Microsoft 365；以配置文件或环境变量登录
Mail(provider="gmail", auth=AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop"))
Mail(account=MailAccount(                   # 其他任何 SMTP / IMAP 服务器
    provider="smtp",
    auth=AppPasswordAuth("you@example.com", "..."),
    servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"),
))
```

| 提供商名称 | 发送方式 | 读取方式 |
|---|---|---|
| `google`（或 `gmail`） | SMTP，`smtp.gmail.com:465`，隐式 TLS | IMAP，`imap.gmail.com` |
| `microsoft` | SMTP，`smtp.office365.com:587`，STARTTLS | IMAP，`outlook.office365.com` |
| `microsoft_graph` | Microsoft Graph，`https://graph.microsoft.com/v1.0`（只能用 OAuth2） | Microsoft Graph |
| `yahoo`、`zoho`、`fastmail` | 465 端口的 SMTP，隐含式 TLS（`smtp.mail.yahoo.com`、`smtp.zoho.com`、`smtp.fastmail.com`）；以应用程序密码登录 | IMAP（`imap.mail.yahoo.com`、`imap.zoho.com`、`imap.fastmail.com`） |
| `icloud` | SMTP，`smtp.mail.me.com:587`，STARTTLS；以应用程序密码登录 | IMAP，`imap.mail.me.com` |
| `file` | 不会发出任何东西：每封邮件都写成 `mail_outbox/Sent` 底下的 `.eml` 档（以 `MAIL_THUNDER_FILE_PROVIDER_DIR` 指定目录） | 文件夹里的 `.eml` 档，例如 `mail_outbox/INBOX` |
| `smtp` | 账号 `MailServers` 指定的 SMTP（465 端口的隐式 TLS，或 `smtp_starttls=True` 的 587 端口） | 账号 `MailServers` 指定的 IMAP |

没有指定提供商名称时，`Mail()` 使用 OAuth2 配置指定的提供商，否则使用 Gmail：与 `smtp_instance`、`imap_instance`
连接的服务器相同。连接一律使用 TLS。新的后端实现 `MailSender` 与／或 `MailStore`，再以
`register_provider(name, factory)` 加入；`Mail` 与使用它的代码都不需要修改。

### 错误

每一次失败都会被记录，并以 `MailThunderException` 的子类抛出（`je_mail_thunder.utils.exception.exceptions`）：

| 异常 | 含义 |
|---|---|
| `MailThunderMessageException` | 邮件无法照现在的样子发出：没有收件人、没有发件人、地址或标头无效 |
| `MailThunderAttachmentException` | 附件不存在或违反策略 |
| `MailThunderAuthenticationException` | 没有认证信息，或服务器拒绝登录 |
| `MailThunderConnectionException` | 无法连上服务器，或连接中断 |
| `MailThunderSendException` | 服务器拒绝这封邮件，或拒绝其中部分收件人（`refused`） |
| `MailThunderProviderException` | 上面两者的基类；未知的提供商、被拒绝的文件夹或未知的邮件标识符也会抛出 |

邮件绝不会发出两次：发送途中发生的失败只会报告，不会重试。空闲时被服务器中断的连接，会在下一次调用前重新建立。

### 从 Wrapper 迁移

`SMTPWrapper`、`IMAPWrapper`、`smtp_instance`、`imap_instance` 以及 `MT_smtp_*` / `MT_imap_*` 指令都照旧运作，
所以代码可以一次只迁移一个调用：

| Wrapper 调用 | `Mail` 调用 |
|---|---|
| `smtp.later_init()` / `imap.later_init()` | 不需要：`Mail` 会在第一次使用时登录 |
| `smtp.create_message_and_send(content, settings)` | `mail.send(to=..., subject=..., text=content)` |
| `smtp.create_message_with_attach_and_send(content, settings, file, use_html=True)` | `mail.send(to=..., subject=..., html=content, attachments=[file])` |
| `imap.select_mailbox("INBOX")` 之后 `imap.mail_content_list()` | `mail.get_messages(folder="INBOX")` |
| `smtp.quit()` / `imap.quit()` | `mail.close()`，或 `with Mail() as mail:` |

```python
from je_mail_thunder import Mail, legacy_message, mail_from_wrappers, smtp_instance

# 把 create_message_and_send / create_message_with_attach_and_send 的参数转成邮件
message = legacy_message("Hello", {"Subject": "Hi", "From": "me@gmail.com", "To": "you@example.com"},
                         attach_file="report.pdf", use_html=False)
Mail().send(message)

# 或沿用已经登录的 wrapper，通过它发送，同时得到 Mail 加上的检查
smtp_instance.later_init()
mail_from_wrappers(smtp=smtp_instance).send(message)
```

差异：wrapper 的方法记录错误后返回 `None`，`Mail` 则会抛出异常；邮件至少要有一位有效的收件人；附件会按策略检查；
读取不会把邮件标成已读，而且得到的是 `MailMessage` 对象，不是 `{"SUBJECT": ..., "BODY": ...}` 字典。

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

### 验证对象

每一种登录方式都是一个 `Authentication` 对象，因此负责连接的代码不需要在意拿到的是哪一种：

| 类 | 登录方式 | 适用于 |
|---|---|---|
| `PasswordAuth(user, password)` | 账号的密码 | SMTP、IMAP |
| `AppPasswordAuth(user, app_password)` | 应用专用密码（Google、Yahoo、iCloud）；显示时夹带的空格会被去除 | SMTP、IMAP |
| `OAuth2Auth(settings)` | OAuth2 访问令牌，以 `Authorization: Bearer ...` 发送 | HTTP API |
| `XOAUTH2Auth(settings)` | 同一个令牌，以 SASL `XOAUTH2` 发送 | SMTP、IMAP、HTTP API |

```python
from je_mail_thunder import AppPasswordAuth, OAuth2Settings, SMTPWrapper, XOAUTH2Auth, resolve_authentication

auth = AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop")
auth = XOAUTH2Auth(OAuth2Settings(user="you@gmail.com", client_id="...", client_secret="...", refresh_token="..."))
auth = resolve_authentication()   # 配置文件或环境变量里的登录方式，没有则为 None

with SMTPWrapper() as smtp:
    auth.login(smtp)              # 同一个调用也能登录 IMAPWrapper
```

`auth.login(client)` 登录 SMTP 或 IMAP wrapper，`auth.authorization()` 返回 HTTP `Authorization` 标头的值。
某个机制做不到其中一项时会抛出 `MailThunderAuthenticationException`；`MailThunderOAuth2Exception` 现在是它的子类。
`settings` 是 `OAuth2Settings`；令牌来自共享的令牌缓存，并在到期前一分钟刷新。`resolve_authentication()` 与 wrapper
一样，有 OAuth2 配置时优先于密码。密码与令牌不会出现在 `repr` 中。把它交给 `Mail(auth=...)` 或
`MailAccount(auth=...)` 就能用它登录。

---

## 附件策略

`AttachmentPolicy` 定义一封邮件可以携带什么。`validate_attachments` 会在发出任何东西之前按策略检查邮件的附件，
并在第一条被违反的规则处抛出结构化异常。

```python
from je_mail_thunder import Attachment, AttachmentPolicy, validate_attachments

policy = AttachmentPolicy(
    max_file_size=10 * 1024 * 1024,     # 单个附件的字节上限
    max_total_size=20 * 1024 * 1024,    # 所有附件合计的字节上限
    max_count=5,
    allowed_extensions={"pdf", "csv", "html"},
    allowed_mime_types={"application/pdf", "text/*"},
)
attachments = [Attachment.from_path("report.pdf"), Attachment.from_path("results.csv")]
total_bytes = validate_attachments(attachments, policy)
```

每个上限都是可选的：默认值 `None` 表示不设限。扩展名比较不区分大小写、有没有点都可以，并以最后一个扩展名为准
（`report.pdf.exe` 是 `.exe`）。MIME 类型可以用 `/*` 结尾。
`DEFAULT_ATTACHMENT_POLICY` 允许单个附件与整封邮件各 25 MiB、任何类型。

检查顺序为：数量 → 是否存在 → 大小 → 扩展名 → MIME 类型 → 合计大小：

| 异常 | 抛出时机 | 属性 |
|---|---|---|
| `AttachmentCountExceeded` | 附件数量超过 `max_count` | `count`、`limit` |
| `AttachmentNotFound` | 要附加的文件不存在 | `path` |
| `AttachmentTooLarge` | 单个附件超过 `max_file_size` | `filename`、`size`、`limit` |
| `AttachmentTypeNotAllowed` | 扩展名或 MIME 类型不在允许范围内 | `filename`、`kind`、`value` |
| `TotalAttachmentSizeExceeded` | 附件合计超过 `max_total_size` | `size`、`limit` |

它们都继承自 `MailThunderAttachmentException`（`je_mail_thunder.utils.exception.exceptions`）。类型检查看的是文件名而不是
内容：它能防止误发错误的文件，无法防止刻意改名的文件。

`Attachment.save(directory)` 用来写入随邮件收到的附件。文件名会先处理成安全的名称：目录部分、`..`、控制字符与
Windows 不接受的字符都会被移除，因此文件不会落在 `directory` 之外。

`Mail` 会在每次 `send` 与 `create_draft` 时套用它的策略。SMTP wrapper 的 `create_message_with_attach_and_send`
会依 wrapper 的 `attachment_policy` 检查文件（默认为 `DEFAULT_ATTACHMENT_POLICY`；可以指定另一个策略，或设为 `None`
关闭检查）：被拒绝的文件会写入日志，邮件不会发出。

---

## 邮件模板

邮件模板包含主题、纯文本正文与 HTML 正文，三者共用同一份 context，所以报表邮件只要写一次，就能带入不同的数字发出：

```python
from je_mail_thunder import Mail

with Mail() as mail:
    mail.send(
        to="qa@example.com",
        template="test_report",
        context={"project": "APITestka", "passed": 98, "failed": 2, "failures": [{"name": "login"}]},
    )
```

`Mail` 以名称寻找模板：先找项目的 `mail/templates/` 目录，再找共用目录（`~/.je_mail_thunder/templates`，或
`$MAIL_THUNDER_TEMPLATE_DIR`）。模板可以是一个 JSON 档 `test_report.json`（`subject` / `text` / `html` / `variables` /
`metadata`），也可以是一个目录：

```
mail/templates/test_report/
  subject.txt      [{{ project }}] {{ passed }} passed, {{ failed }} failed
  body.txt         plain-text body
  body.html        HTML body (values are HTML-escaped)
  template.json    {"variables": {"project": {}, "failed": {"default": 0}}, "metadata": {"owner": "qa"}}
```

语法是 Jinja2 中邮件用得到的部分，以标准库实现：

| 语法 | 意义 |
|---|---|
| `{{ user.name }}` | 一个值；以点号取得 dict、list（`items.0`）与公开属性的内容 |
| `{{ name \| upper }}` | 过滤器：`upper`、`lower`、`title`、`trim`、`length`、`join(", ")`、`default("x")`、`safe` |
| `{% if failed > 0 %} … {% elif skipped %} … {% else %} … {% endif %}` | 条件：一个值、`not`，或一次比较（`== != < <= > >=`） |
| `{% for test in failures %} {{ loop.index }}. {{ test.name }} {% endfor %}` | 循环，可用 `loop.index`、`loop.first`、`loop.last`、`loop.length` |
| `{# note #}` | 注释 |

模板只能读取 context：其中没有任何内容会被当成 Python 运行，HTML 正文中的每个值都会做 HTML 转义，除非经过 `safe`。
在 `variables` 声明的变量会在产生内容之前检查，`TemplateContextError.missing` 会列出所有缺少的变量；有 `default` 的变量
是可选的。`mail.render("test_report", context)` 返回产生出来的主题、纯文本与 HTML，不会发出；与 `template=` 同时给的
字段（例如 `subject=`）优先于模板产生的结果。错误都是 `MailThunderTemplateException` 的子类：`TemplateNotFound`、
`TemplateSyntaxError`、`TemplateContextError`、`TemplateRenderError`。

模板也可以在程序中创建：`mail.templates.add(MailTemplate("welcome", subject="Hi {{ name }}", text="..."))`。

---

## 邮件事件与触发器

`Mail` 会把邮件发生的事情以事件回报，不论提供商是哪一家都用同一套名称；触发器后端则负责监看文件夹，让新邮件也成为事件：

```python
from je_mail_thunder import Mail

mail = Mail()

def handle_report(event):
    print(event.message.sender, event.message.subject)

mail.on("message_received", handle_report, filter={"subject": "[TEST]", "has_attachments": True})
mail.watch("INBOX")                  # 在背景线程每 60 秒查看一次
mail.watch("INBOX", idle=True)       # 或由服务器通知新邮件（IMAP IDLE）

@mail.on("message_failed")           # on() 也可以当作装饰器
def alert(event):
    print("not sent:", event.error)
```

| 事件 | 发生时机 |
|---|---|
| `message_received`、`attachment_received` | 被监看的文件夹有新邮件（它的每个附件各一次） |
| `message_sent` | `send` 已把邮件交给提供商 |
| `message_failed` | `send` 或 `create_draft` 失败，不论原因 |
| `attachment_rejected` | 附件不存在或违反附件策略 |
| `authentication_failed`、`connection_failed` | 没有认证信息或登录被拒；无法连上服务器或连接中断 |

处理函数会收到一个 `MailEvent`（`name`、`message`、`attachment`、`error`、`provider`、`folder`、`timestamp`、`metadata`）。
`filter` 可以是规则的 mapping（`sender`、`recipient`、`subject`、`body`、`has_attachments`、`attachment_type`、`since`、
`until`、`metadata`）、接收事件的函数，或 `MailFilter`；文本规则不分大小写，也可以使用编译过的正则表达式。
失败仍然会以异常回报给调用端；处理函数抛出的异常只会被记录，不会中断其他事情。

`mail.watch(folder, interval=60, idle=False, start=True, include_existing=False)` 会在 `mail.triggers` 加入一个后端：
`IMAPPollingBackend`（只搜索比上次看到的更大的 UID）、`IMAPIdleBackend`，或是适用于其他 `MailStore` 的 `PollingBackend`。
监看使用自己的连接，第一次查看只会记下已经存在的邮件；`mail.triggers.poll()` 则是只查看一次，不启动线程。
在动作文件中，`MT_mail_poll` 会返回上一次 `MT_mail_poll` 以来的事件。

---

## Microsoft Graph

`microsoft_graph` 提供商通过 Microsoft Graph API 访问 Microsoft 365 邮箱，而不是 SMTP 与 IMAP。`Mail` 的调用方式完全相同，
只有提供商名称不同：

```python
from je_mail_thunder import Mail, OAuth2Auth, OAuth2Settings

auth = OAuth2Auth(OAuth2Settings(
    user="you@contoso.com", provider="microsoft", tenant="contoso.onmicrosoft.com",
    client_id="...", client_secret="...", refresh_token="...",
))
with Mail(provider="microsoft_graph", auth=auth) as mail:
    mail.send(to="qa@example.com", subject="Report", html="<b>42 passed</b>", attachments=["report.pdf"])
    for message in mail.get_messages(limit=10, unread_only=True):
        print(message.sender, message.subject)
```

- **如何可选**：在程序中使用 `Mail(provider="microsoft_graph")`。对 `Mail()` 与 `MT_mail_*` 指令，则在
  `mail_thunder_content.json` 设置 `"mail_provider": "microsoft_graph"`，或设置环境变量 `mail_thunder_mail_provider`
  （它可以是任何已注册的提供商）。`microsoft` 仍然代表 SMTP 与 IMAP。
- **登录**：只能用 OAuth2。应用程序注册需要委派权限 `Mail.Send` 与 `Mail.ReadWrite`。OAuth2 设置没有指定 `scope` 时，
  会以 Graph 的 scope 取得令牌。
- **发送**：附件不大时是一次 `sendMail` 请求；否则先创建草稿，把每个附件加上去（超过 3 MiB 的走 upload session），
  再把草稿发出。
- **读取**：文件夹可以是 `INBOX`、`Drafts`、`Sent`、`Deleted Items`、`Junk`、`Archive` 或显示名称；`query=` 是 OData 的
  `$filter` 表达式，例如 `from/emailAddress/address eq 'ci@example.com'`。
- **与 SMTP 的差异**：邮件只有一个正文（两者都给时使用 HTML）、自订标头必须以 `X-` 开头、`sender` 若不是帐号本人
  需要「以…身分发送」权限。
- **触发器**：`mail.watch()` 会使用 `GraphPollingBackend`。`GraphWebhookBackend(provider, "https://your.host/hook")`
  让 Graph 主动通知新邮件：它的监听器绑定 `localhost:9946`，放在你的 HTTPS 代理之后，会回应 Graph 的验证，
  并忽略没有带着密钥的通知。

请求只会送往 `https://graph.microsoft.com`；令牌被拒绝时会抛出 `MailThunderAuthenticationException`。

---

## 监控

三种监听者把[邮件事件](#邮件事件与触发器)变成事后可以查看的数据。它们都挂在 `mail.events` 上，而且都不会让邮件停下来：

```python
from je_mail_thunder import AuditLog, Mail, ProviderHealth, WebhookForwarder

mail = Mail()
audit, health = AuditLog(), ProviderHealth()
audit.attach(mail.events)                 # 每个事件一行 JSON，写入 ~/.je_mail_thunder/audit/mail_audit.jsonl
health.attach(mail.events)                # 每个提供商的 healthy / degraded / down 状态
mail.on("*", WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret"))

print(health.report())                    # [{"provider": "smtp", "state": "healthy", ...}]
print(health.probe(mail.providers))       # 立刻要求每个提供商连接并登录
print(audit.entries(limit=10))
```

- **`AuditLog(path=None, subjects=True)`** 记录谁在什么时候发出或收到了什么：地址、主题、附件名称与大小、提供商，
  以及失败时的错误。不会记录正文、附件内容或任何认证信息。文件只会附加（可用 `MAIL_THUNDER_AUDIT_FILE` 改变位置），
  超过 10 MiB 时会轮替。
- **`ProviderHealth(failure_threshold=3)`** 在成功后是 `healthy`，失败后是 `degraded`，连续失败 `failure_threshold` 次后
  是 `down`。只有提供商本身的失败才会计入（登录被拒、连接中断、邮件被拒绝），缺少收件人或附件被拒绝不算。
  `probe` 会调用每个提供商的 `check()`。
- **`WebhookForwarder(url, secret=None, bodies=False)`** 通过背景队列把每个事件以 JSON POST 到一个 `https` 地址，
  所以接收端再慢也不会拖慢 `send`。有 `secret` 时，每个请求都带有
  `X-MailThunder-Signature: sha256=<内容的 HMAC-SHA256>`。除非 `bodies=True`，否则不包含邮件正文。

---

## 项目邮件层

自动化项目把「怎么寄信」放在自己的 `mail/` 目录里，程序只要取得一个设置好的 `Mail`，不必指定提供商。之后要把项目
换到另一家提供商，或是不发出任何东西先试跑，都只需要修改一个文件：

```
MyProject/
  mail/
    config.py       # PROVIDER, AUTH or ACCOUNT, ATTACHMENT_POLICY, AUDIT (all optional)
    triggers.py     # register(mail): event handlers and watched folders
    templates/      # the project's mail templates
```

```python
from je_mail_thunder import project_mail

mail = project_mail()                    # 工作目录中的项目
mail.send(to="qa@example.com", template="test_report",
          context={"project": "MyProject", "passed": 98, "failed": 2})
mail.triggers.poll()                     # 查看一次有没有新邮件
mail.close()
```

- **`config.py`** 可以设置 `PROVIDER`（已注册的提供商名称）、`AUTH` 或完整的 `ACCOUNT`、`ATTACHMENT_POLICY`，以及 `AUDIT`
  （`True` 会把每个邮件事件记录到 `mail/audit.jsonl`）。省略 `AUTH` 时登录信息来自 `mail_thunder_content.json` 或
  环境变量，这样认证信息就不会出现在项目的文件里。
- **`triggers.py`** 定义 `register(mail)`，负责订阅项目的处理函数（`mail.on(...)`）并指定要监看的文件夹（`mail.watch(...)`）。
- **`templates/`** 会比共用模板先被搜索。

`create_project_dir()` 会创建这一层，内含 `test_report` 模板并使用 `file` 提供商，所以新项目在指定真正的提供商之前，
邮件都只会留在磁盘上。`project_mail()` 会运行 `config.py` 与 `triggers.py`，它们是项目的 Python 档：只加载你信任的项目。
没有任何动作指令会加载这一层；`describe_mail_layer()` 则只列出文件，不会运行它们。

---

## MailThunder Studio

MailThunder Studio 是一个在本机打开的页面，用来查看并试用邮件 API 目前的设置。它由标准库提供服务、不需要额外的
套件，而且只会调用[内核邮件 API](#内核邮件-api)，所以不论使用哪一家提供商都一样运作：

```bash
python -m je_mail_thunder.studio                       # 使用配置文件或环境变量里的帐号
python -m je_mail_thunder.studio --project MyProject   # 使用某个项目的邮件层（会运行它的 mail/config.py 与 mail/triggers.py）
python -m je_mail_thunder.studio --port 9950 --no-browser
```

它会印出像 `http://localhost:9947/#token=...` 这样的地址并打开它。页面有 English 与中文两种语言。

| 页面 | 显示与可运行的内容 |
|---|---|
| 仪表盘 | 帐号（绝不显示密码或令牌）、每个提供商的健康状态、各项数量、最新的审计纪录，以及一个可以寄信的表单 |
| 帐号 | 帐号与其服务器、已注册的提供商，以及要求每个提供商连接并登录的按钮 |
| 模板 | 每个模板与其变量；输入 JSON 格式的 context 就能产生内容，不会发出 |
| 触发器 | 事件、已订阅的处理函数与过滤条件、触发器后端，以及立即查看一次新邮件的按钮 |
| 策略 | 附件策略，可以修改，变更在 Studio 运行期间有效 |
| 项目 | 项目邮件层的文件与模板；不会运行其中任何文件 |
| 日志 | 日志档的结尾与审计日志 |
| 设置 | MailThunder 存放文件的位置、已注册的提供商，以及运行环境的版本 |

Studio 是给坐在这台电脑前的人使用的工具。它使用纯 HTTP，所以只在 loopback 地址上提供服务（`localhost`，或以 `--host`
指定 `127.x.x.x`），其他地址一律拒绝；要从另一台机器使用，请通过 SSH 转发端口（`ssh -L 9947:localhost:9947 host`）。
每个 API 请求都需要该次运行的随机令牌，令牌放在地址的
fragment 里，浏览器不会把它送给任何服务器；`Host` 不同的请求会被拒绝；页面不会从其他地方加载任何东西，所有内容都以
文本写入，所以通过邮件送来的内容无法在浏览器中运行；任何回应都不包含密码或令牌；从页面发出的邮件也不能指定附件。
不使用时请把它停掉。`je_mail_thunder.studio.server` 的 `start_studio(mail)` 可以从 Python 启动它。

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
| `MT_mail_send` | 通过配置的提供商发送邮件 | `{"to": str 或 list, "subject": str, "text": str, "html": str, "cc": ..., "bcc": ..., "attachments": [路径], "sender": str, "reply_to": ..., "headers": dict}` |
| `MT_mail_create_draft` | 将邮件存成草稿 | `MT_mail_send` 的参数，另加 `"folder": str` |
| `MT_mail_get_messages` | 取得文件夹的邮件，最新的在前 | `{"folder": str, "limit": int, "unread_only": bool, "query": str}`（默认：INBOX、不限数量） |
| `MT_mail_get_message` | 按标识符取得一封邮件 | `{"message_id": str, "folder": str}` |
| `MT_mail_delete_message` | 按标识符删除一封邮件 | `{"message_id": str, "folder": str}` |
| `MT_mail_close` | 关闭提供商的连接 | 无 |
| `MT_mail_render_template` | 产生邮件模板的内容，不发出 | `{"template": str, "context": dict}` |
| `MT_mail_poll` | 取得文件夹自上次轮询以来新邮件的事件 | `{"folder": str}`（默认：INBOX） |
| `MT_set_mail_thunder_os_environ` | 设置验证环境变量 | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | 获取验证环境变量 | 无 |
| `MT_add_package_to_executor` | 加载 Python 包至执行器 | `["包名称"]` |

`MT_mail_*` 指令在 `mail_instance` 上使用[核心邮件 API](#核心邮件-api)；`mail_instance` 是一个使用配置文件或环境变量
账号的 `Mail()`。这些指令在第一次使用时才连接，并返回可转成 JSON 的值。它的附件策略只能从 Python 设置
（`mail_instance.policy = AttachmentPolicy(...)`），不能由动作设置，所以动作文件无法放宽它。

**示例 — 通过核心邮件 API 发送邮件并读取收件箱：**

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
  mail/
    config.py              # 项目的提供商、附件策略与审计日志
    triggers.py            # register(mail)：事件处理函数与要监看的文件夹
    templates/test_report/ # subject.txt、body.txt、body.html、template.json
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

### Mail

`Mail(provider=None, auth=None, account=None, policy=None, providers=None)`：与提供商无关的 API。可作为
context manager；第一次调用之前不会连接。

| 方法 | 说明 |
|------|------|
| `send(message=None, **fields)` | 检查并发送 `MailMessage`，或由 `fields` 创建的邮件；返回该邮件 |
| `create_draft(message=None, folder=None, **fields)` | 检查邮件并存成草稿；返回其标识符，或 `None` |
| `get_messages(folder="INBOX", limit=None, unread_only=False, query=None)` | 迭代文件夹的邮件，最新的在前 |
| `get_message(message_id, folder="INBOX")` | 返回一封邮件 |
| `delete_message(message_id, folder="INBOX")` | 删除一封邮件 |
| `close()` | 关闭连接；下一次调用会重新连接 |

| 名称 | 说明 |
|------|------|
| `MailMessage(subject, to, cc, bcc, sender, reply_to, text, html, attachments, headers, message_id, date)` | 与提供商无关的邮件；`to_dict()` 返回可转成 JSON 的值 |
| `MailAccount(provider="google", auth=None, servers=None)` / `MailServers(smtp_host, smtp_port, smtp_starttls, imap_host, drafts_folder)` | 谁的邮件、在哪些服务器上、用哪种方式登录 |
| `MailSender` / `MailStore` / `register_provider(name, factory)` | 提供商接口与注册表；`SMTPProvider` 与 `IMAPProvider` 实现了它们 |
| `mail_instance` | `MT_mail_*` 指令使用的 `Mail()` |
| `legacy_message(...)` / `mail_from_wrappers(smtp=None, imap=None, policy=None)` | 从 wrapper API 过渡的桥接函数 |

### SMTPWrapper

继承自 `smtplib.SMTP_SSL`（经由 `SMTPClientMixin`）。默认主机：`smtp.gmail.com`，默认端口：`465`。

所有 SMTP 与 IMAP 连接都会依系统的信任证书库验证服务器的证书与主机名（`smtplib.SMTP_SSL` 与 `imaplib.IMAP4_SSL`
本身两者都不检查）。使用自签名证书或私有证书颁发机构的服务器会被拒绝并抛出 `ssl.SSLCertVerificationError`，直到在
`SSL_CERT_FILE`（或 `SSL_CERT_DIR`）环境变量中指定包含该证书的 CA bundle 为止。

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

继承自 `imaplib.IMAP4_SSL`。默认主机：`imap.gmail.com`。与 SMTP 相同，会验证服务器的证书与主机名。

| 方法 | 说明 |
|------|------|
| `later_init()` | 使用配置文件或环境变量登录（有 OAuth2 配置时用 OAuth2） |
| `select_mailbox(mailbox="INBOX", readonly=False)` | 选择邮箱，返回 `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | 搜索并返回原始邮件详细信息列表 |
| `mail_content_list(search_str="ALL", charset=None)` | 返回已解析的邮件内容字典列表 |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主题为文件名导出所有邮件；路径分隔符号、控制字符与 `: * ? " < > \|` 会被换成 `_` |
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
    attachments/             # 附件模型、AttachmentPolicy 与验证器
    auth/                    # 验证机制：密码、应用专用密码、OAuth2、XOAUTH2
    core/                    # Mail（与提供商无关的 API）、MailMessage、MailAccount
    providers/               # MailSender / MailStore 接口、SMTPProvider、IMAPProvider、注册表
    templates/               # 邮件模板：模板语法、MailTemplate、TemplateLoader
    triggers/                # 邮件事件：过滤器、dispatcher、轮询与 IMAP IDLE 后端
    monitoring/              # AuditLog 与 ProviderHealth，由邮件事件驱动
    studio/                  # MailThunder Studio：本机页面、它的 API 与 HTTP 服务器
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
      tls/                   # 每个 SMTP / IMAP 连接使用的、会验证证书的 TLS context
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
