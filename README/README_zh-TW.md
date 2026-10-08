# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** 是一款輕量且靈活的 Python 電子郵件自動化工具。它與供應商無關的 `Mail` API 不論背後是哪一家供應商，都以同樣的方式寄信與讀信；它封裝了 SMTP 和 IMAP4 協定，提供 JSON 腳本引擎與專案模板功能，讓寄信、收信與管理郵件內容變得輕鬆簡單。

**[English](../README.md)** | **[简体中文](README_zh-CN.md)**

---

## 目錄

- [功能特色](#功能特色)
- [系統需求](#系統需求)
- [安裝](#安裝)
- [快速開始](#快速開始)
  - [設定](#設定)
  - [寄送郵件 (SMTP)](#寄送郵件-smtp)
  - [寄送帶附件的郵件](#寄送帶附件的郵件)
  - [讀取郵件 (IMAP)](#讀取郵件-imap)
  - [匯出所有郵件為檔案](#匯出所有郵件為檔案)
- [核心郵件 API](#核心郵件-api)
  - [寄送郵件 (Mail)](#寄送郵件-mail)
  - [讀取、草稿與刪除](#讀取草稿與刪除)
  - [帳號與供應商](#帳號與供應商)
  - [錯誤](#錯誤)
  - [從 Wrapper 遷移](#從-wrapper-遷移)
- [身份驗證](#身份驗證)
  - [JSON 設定檔](#json-設定檔)
  - [環境變數](#環境變數)
  - [OAuth2（Google 與 Microsoft）](#oauth2google-與-microsoft)
  - [驗證物件](#驗證物件)
- [附件政策](#附件政策)
- [郵件模板](#郵件模板)
- [郵件事件與觸發器](#郵件事件與觸發器)
- [Microsoft Graph](#microsoft-graph)
- [監控](#監控)
- [專案郵件層](#專案郵件層)
- [MailThunder Studio](#mailthunder-studio)
- [腳本引擎](#腳本引擎)
  - [Action JSON 格式](#action-json-格式)
  - [可用的腳本指令](#可用的腳本指令)
  - [擴充自訂指令](#擴充自訂指令)
  - [動態載入套件](#動態載入套件)
- [專案模板](#專案模板)
- [命令列介面](#命令列介面)
- [Socket 伺服器](#socket-伺服器)
- [API 參考](#api-參考)
  - [Mail](#mail)
  - [SMTPWrapper](#smtpwrapper)
  - [SMTPStartTLSWrapper](#smtpstarttlswrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函式](#executor-函式)
  - [工具函式](#工具函式)
- [專案結構](#專案結構)
- [授權條款](#授權條款)

---

## 功能特色

- **與供應商無關的 `Mail` API** — 一個物件就能寄送、讀取、建立草稿與刪除郵件；背後是可以接上新後端的供應商介面（目前為 SMTP 與 IMAP）
- **郵件模板** — 主旨、純文字與 HTML 模板，支援 Jinja2 風格的 `{{ }}`、`{% if %}` 與 `{% for %}`，以標準函式庫實作：`mail.send(template=..., context=...)`
- **郵件事件與觸發器** — `mail.on("message_received", handler, filter={...})` 提供與供應商無關的事件，`mail.watch()` 以輪詢或 IMAP IDLE 監看新郵件
- **Microsoft Graph 供應商** — 以 OAuth2 透過 Graph API 寄送、建立草稿、讀取與刪除 Microsoft 365 郵件，並提供輪詢與 webhook 觸發器
- **監控** — 只能附加的稽核日誌、每個供應商的健康報告，以及帶簽章的對外 webhook，全部由郵件事件驅動
- **更多供應商** — Yahoo、iCloud、Zoho 與 Fastmail 的預設值，以及把郵件留在磁碟上、供試跑使用的 `file` 供應商
- **專案郵件層** — 專案把供應商、政策、模板與觸發器放在 `mail/`，`project_mail()` 就能給程式一個設定好的 `Mail`
- **MailThunder Studio** — 本機頁面（`python -m je_mail_thunder.studio`），可查看帳號、模板、觸發器、政策、專案郵件層與日誌，由標準函式庫提供服務
- **SMTP 支援** — 透過隱含式 TLS 寄送郵件，預設使用 Gmail，也可自訂其他 SMTP 服務；或透過 STARTTLS（Microsoft 365）
- **IMAP4 支援** — 透過 IMAP4 SSL 讀取、搜尋和匯出郵件
- **附件處理** — 自動偵測文字、圖片、音訊和二進位檔案的 MIME 類型
- **附件政策** — 寄送前檢查附件的數量、大小、副檔名與 MIME 類型，每條規則都有對應的結構化例外
- **HTML 郵件** — 支援寄送 HTML 格式的郵件與附件
- **JSON 腳本引擎** — 使用 JSON 動作檔自動化郵件工作流程
- **專案模板** — 快速建立包含預設關鍵字和執行器模板的專案
- **Socket 伺服器** — 透過 TCP Socket 遠端控制 MailThunder
- **套件管理器** — 動態載入 Python 套件至腳本執行器
- **環境變數驗證** — 支援設定檔或作業系統環境變數進行身份驗證
- **OAuth2 登入** — Gmail 與 Microsoft 365 的 SASL `XOAUTH2`，以標準函式庫交換 refresh token 並快取存取權杖
- **驗證物件** — `PasswordAuth`、`AppPasswordAuth`、`OAuth2Auth` 與 `XOAUTH2Auth`，共用同一個 `Authentication` 介面
- **自動匯出** — 一行指令即可將信箱所有郵件匯出為本機檔案
- **Context Manager 支援** — SMTP 和 IMAP 連線皆可使用 `with` 語法
- **日誌記錄** — 內建所有操作的日誌紀錄

---

## 系統需求

- Python 3.10 或更新版本
- `je_action_core`，安裝時會一併裝上：MailThunder 與 APITestka、LoadDensity、FileAutomation 共用的 action 執行器（它只用 Python 標準函式庫）

---

## 安裝

**穩定版：**

```bash
pip install je_mail_thunder
```

**開發版：**

```bash
pip install je_mail_thunder_dev
```

`je_mail_thunder_dev` 跟著 `dev` 分支走：每次推送到 `dev` 通過測試、而且套件內容有變動時，CI 就會發佈一個新版本。

---

## 快速開始

### 設定

使用 MailThunder 之前，需要先設定身份驗證。在目前工作目錄下建立一個名為 `mail_thunder_content.json` 的檔案：

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

> **重要提示：** 若使用 Gmail，必須使用[應用程式密碼](https://support.google.com/accounts/answer/185833)，而非一般的 Google 帳戶密碼。同時需要在 Gmail 設定中[啟用 IMAP](https://support.google.com/mail/answer/7126229?hl=zh-Hant)。

### 寄送郵件 (SMTP)

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()  # 使用設定檔或環境變數登入
    smtp.create_message_and_send(
        message_content="來自 MailThunder 的問候！",
        message_setting_dict={
            "Subject": "測試郵件",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        }
    )
```

### 寄送帶附件的郵件

```python
from je_mail_thunder import SMTPWrapper

with SMTPWrapper() as smtp:
    smtp.later_init()
    smtp.create_message_with_attach_and_send(
        message_content="請查看附件。",
        message_setting_dict={
            "Subject": "帶附件的郵件",
            "From": "sender@gmail.com",
            "To": "receiver@gmail.com"
        },
        attach_file="/path/to/file.pdf",
        use_html=False  # 若 message_content 為 HTML 則設為 True
    )
```

### 讀取郵件 (IMAP)

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()  # 登入
    imap.select_mailbox("INBOX")
    emails = imap.mail_content_list()
    for mail in emails:
        print(f"主旨: {mail['SUBJECT']}")
        print(f"寄件者: {mail['FROM']}")
        print(f"內容: {mail['BODY'][:100]}...")
```

### 匯出所有郵件為檔案

```python
from je_mail_thunder import IMAPWrapper

with IMAPWrapper() as imap:
    imap.later_init()
    imap.select_mailbox("INBOX")
    imap.output_all_mail_as_file()  # 以郵件主旨為檔名儲存每封郵件
```

---

## 核心郵件 API

`Mail` 是與供應商無關的 API：不論帳號用的是哪一家供應商，都用同一組呼叫來寄送、讀取、建立草稿與刪除郵件。
它使用[身份驗證](#身份驗證)一節說明的認證資訊，在第一次使用時才連線，之後的呼叫沿用同一條連線；
發生錯誤時會引發例外，而不是只寫入日誌。

### 寄送郵件 (Mail)

```python
from je_mail_thunder import Mail

with Mail() as mail:                       # Gmail，或 OAuth2 設定指定的供應商
    mail.send(
        to="receiver@example.com",         # 一個位址、以逗號分隔的多個位址，或清單
        cc=["team@example.com"],
        subject="Nightly report",
        text="42 passed, 0 failed.",
        html="<b>42</b> passed, 0 failed.",
        attachments=["report.html"],
    )
```

`text` 與 `html` 都給時，郵件會同時攜帶兩種版本。寄件者預設為帳號的使用者，也可以用 `sender=` 指定；
另外接受 `bcc`、`reply_to` 與 `headers`。在任何資料送到伺服器之前，郵件會先經過檢查：至少一位收件者、
位址有效、主旨與標頭的值為單行（因此無法透過某個值夾帶第二個標頭），以及附件是否符合[附件政策](#附件政策)
（`Mail(policy=...)`；預設為 25 MiB、任何類型）。

### 讀取、草稿與刪除

```python
from je_mail_thunder import Mail

with Mail() as mail:
    for message in mail.get_messages(folder="INBOX", limit=10, unread_only=True):
        print(message.message_id, message.sender, message.subject)
        for attachment in message.attachments:
            attachment.save("downloads")    # 寫入的檔名不會離開該目錄

    message = mail.get_message("4321")      # 使用 get_messages 給的 message_id
    mail.create_draft(to="receiver@example.com", subject="Later", text="...")
    mail.delete_message("4321")
```

`get_messages` 回傳迭代器，最新的郵件在前：郵件一封一封取回，不會把整個大信箱放進記憶體，而且讀取不會把郵件
標成已讀。`query=` 接受供應商自己的搜尋語法（IMAP `SEARCH` 條件，例如 `'FROM "ci@example.com" SINCE 1-Oct-2026'`）。
每封郵件都是 `MailMessage`，有 `subject`、`sender`、`to`、`cc`、`reply_to`、`date`、`text`、`html`、`attachments`、
`headers` 與 `message_id`。

### 帳號與供應商

```python
from je_mail_thunder import AppPasswordAuth, Mail, MailAccount, MailServers

Mail(provider="microsoft")                  # Microsoft 365；以設定檔或環境變數登入
Mail(provider="gmail", auth=AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop"))
Mail(account=MailAccount(                   # 其他任何 SMTP / IMAP 伺服器
    provider="smtp",
    auth=AppPasswordAuth("you@example.com", "..."),
    servers=MailServers(smtp_host="smtp.example.com", imap_host="imap.example.com"),
))
```

| 供應商名稱 | 寄送方式 | 讀取方式 |
|---|---|---|
| `google`（或 `gmail`） | SMTP，`smtp.gmail.com:465`，隱含式 TLS | IMAP，`imap.gmail.com` |
| `microsoft` | SMTP，`smtp.office365.com:587`，STARTTLS | IMAP，`outlook.office365.com` |
| `microsoft_graph` | Microsoft Graph，`https://graph.microsoft.com/v1.0`（只能用 OAuth2） | Microsoft Graph |
| `yahoo`、`zoho`、`fastmail` | 465 埠的 SMTP，隱含式 TLS（`smtp.mail.yahoo.com`、`smtp.zoho.com`、`smtp.fastmail.com`）；以應用程式密碼登入 | IMAP（`imap.mail.yahoo.com`、`imap.zoho.com`、`imap.fastmail.com`） |
| `icloud` | SMTP，`smtp.mail.me.com:587`，STARTTLS；以應用程式密碼登入 | IMAP，`imap.mail.me.com` |
| `file` | 不會寄出任何東西：每封郵件都寫成 `mail_outbox/Sent` 底下的 `.eml` 檔（以 `MAIL_THUNDER_FILE_PROVIDER_DIR` 指定目錄） | 資料夾裡的 `.eml` 檔，例如 `mail_outbox/INBOX` |
| `smtp` | 帳號 `MailServers` 指定的 SMTP（465 埠的隱含式 TLS，或 `smtp_starttls=True` 的 587 埠） | 帳號 `MailServers` 指定的 IMAP |

沒有指定供應商名稱時，`Mail()` 使用 OAuth2 設定指定的供應商，否則使用 Gmail：與 `smtp_instance`、`imap_instance`
連線的伺服器相同。連線一律使用 TLS。新的後端實作 `MailSender` 與／或 `MailStore`，再以
`register_provider(name, factory)` 加入；`Mail` 與使用它的程式都不需要修改。

### 錯誤

每一次失敗都會被記錄，並以 `MailThunderException` 的子類別引發（`je_mail_thunder.utils.exception.exceptions`）：

| 例外 | 意義 |
|---|---|
| `MailThunderMessageException` | 郵件無法照現在的樣子寄出：沒有收件者、沒有寄件者、位址或標頭無效 |
| `MailThunderAttachmentException` | 附件不存在或違反政策 |
| `MailThunderAuthenticationException` | 沒有認證資訊，或伺服器拒絕登入 |
| `MailThunderConnectionException` | 無法連上伺服器，或連線中斷 |
| `MailThunderSendException` | 伺服器拒絕這封郵件，或拒絕其中部分收件者（`refused`） |
| `MailThunderProviderException` | 上面兩者的基底；未知的供應商、被拒絕的資料夾或未知的郵件識別碼也會引發 |

郵件絕不會寄出兩次：寄送途中發生的失敗只會回報，不會重試。閒置時被伺服器中斷的連線，會在下一次呼叫前重新建立。

### 從 Wrapper 遷移

`SMTPWrapper`、`IMAPWrapper`、`smtp_instance`、`imap_instance` 以及 `MT_smtp_*` / `MT_imap_*` 指令都照舊運作，
所以程式可以一次只搬一個呼叫：

| Wrapper 呼叫 | `Mail` 呼叫 |
|---|---|
| `smtp.later_init()` / `imap.later_init()` | 不需要：`Mail` 會在第一次使用時登入 |
| `smtp.create_message_and_send(content, settings)` | `mail.send(to=..., subject=..., text=content)` |
| `smtp.create_message_with_attach_and_send(content, settings, file, use_html=True)` | `mail.send(to=..., subject=..., html=content, attachments=[file])` |
| `imap.select_mailbox("INBOX")` 之後 `imap.mail_content_list()` | `mail.get_messages(folder="INBOX")` |
| `smtp.quit()` / `imap.quit()` | `mail.close()`，或 `with Mail() as mail:` |

```python
from je_mail_thunder import Mail, legacy_message, mail_from_wrappers, smtp_instance

# 把 create_message_and_send / create_message_with_attach_and_send 的引數轉成郵件
message = legacy_message("Hello", {"Subject": "Hi", "From": "me@gmail.com", "To": "you@example.com"},
                         attach_file="report.pdf", use_html=False)
Mail().send(message)

# 或沿用已經登入的 wrapper，透過它寄送，同時得到 Mail 加上的檢查
smtp_instance.later_init()
mail_from_wrappers(smtp=smtp_instance).send(message)
```

差異：wrapper 的方法記錄錯誤後回傳 `None`，`Mail` 則會引發例外；郵件至少要有一位有效的收件者；附件會依政策檢查；
讀取不會把郵件標成已讀，而且得到的是 `MailMessage` 物件，不是 `{"SUBJECT": ..., "BODY": ...}` 字典。

---

## 身份驗證

MailThunder 以密碼或 OAuth2 登入。它會先讀 JSON 設定檔，再讀環境變數；有 OAuth2 設定時，以 OAuth2 取代密碼。

### JSON 設定檔

在目前工作目錄下放置 `mail_thunder_content.json`：

```json
{
  "user": "your_email@gmail.com",
  "password": "your_app_password"
}
```

### 環境變數

在執行腳本前設定以下環境變數：

```python
from je_mail_thunder import set_mail_thunder_os_environ

set_mail_thunder_os_environ(
    mail_thunder_user="your_email@gmail.com",
    mail_thunder_user_password="your_app_password"
)
```

或在 Shell 中設定：

```bash
export mail_thunder_user="your_email@gmail.com"
export mail_thunder_user_password="your_app_password"
```

### OAuth2（Google 與 Microsoft）

Google 與 Microsoft 都在淘汰郵件的密碼登入。使用 OAuth2 時，MailThunder 在服務商的權杖端點以 refresh token 換取短效的
存取權杖（只用標準函式庫，且必須是 `https`），再以 SASL `XOAUTH2` 登入。client ID、client secret 與 refresh token
要先透過服務商的授權流程取得一次（Google Cloud 的 OAuth 用戶端，或 Microsoft Entra 的應用程式註冊）；MailThunder
不執行那個流程。

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

或用環境變數：`mail_thunder_user` 加上 `mail_thunder_oauth2_provider`、`mail_thunder_oauth2_client_id`、`mail_thunder_oauth2_client_secret`、`mail_thunder_oauth2_refresh_token`；選用 `mail_thunder_oauth2_tenant`、`mail_thunder_oauth2_scope`、`mail_thunder_oauth2_token_url`、`mail_thunder_oauth2_access_token`（直接使用給定的權杖）。

| 服務商 | SMTP | IMAP | 要求的範圍 |
|---|---|---|---|
| `google`（預設） | `smtp.gmail.com:465`，隱含式 TLS（`SMTPWrapper`） | `imap.gmail.com` | `https://mail.google.com/` |
| `microsoft` | `smtp.office365.com:587`，STARTTLS（`SMTPStartTLSWrapper`） | `outlook.office365.com` | `https://outlook.office.com/` 上的 `SMTP.Send`、`IMAP.AccessAsUser.All`，以及 `offline_access` |

`smtp_instance` 與 `imap_instance`（以及 `MT_smtp_*`／`MT_imap_*` 指令）會連到設定所指服務商的伺服器，所以動作檔也能
用 Microsoft。存取權杖會快取，並在到期前一分鐘更新。其他服務商可用 `token_url`（與 `scope`），再以它的主機自行建立
wrapper。祕密不會出現在日誌或錯誤訊息裡。

在 Python 中：

```python
from je_mail_thunder import OAuth2Settings, SMTPStartTLSWrapper, oauth2_token_cache

settings = OAuth2Settings(user="you@contoso.com", provider="microsoft", client_id="...",
                          client_secret="...", refresh_token="...", tenant="contoso.onmicrosoft.com")
with SMTPStartTLSWrapper() as smtp:
    smtp.oauth2_login(settings.user, oauth2_token_cache.access_token(settings))
    smtp.create_message_and_send("Hello", {"Subject": "Hi", "From": settings.user, "To": "friend@example.com"})
```

### 驗證物件

每一種登入方式都是一個 `Authentication` 物件，因此負責連線的程式不需要在意拿到的是哪一種：

| 類別 | 登入方式 | 適用於 |
|---|---|---|
| `PasswordAuth(user, password)` | 帳號的密碼 | SMTP、IMAP |
| `AppPasswordAuth(user, app_password)` | 應用程式密碼（Google、Yahoo、iCloud）；顯示時夾帶的空白會被去除 | SMTP、IMAP |
| `OAuth2Auth(settings)` | OAuth2 存取權杖，以 `Authorization: Bearer ...` 送出 | HTTP API |
| `XOAUTH2Auth(settings)` | 同一個權杖，以 SASL `XOAUTH2` 送出 | SMTP、IMAP、HTTP API |

```python
from je_mail_thunder import AppPasswordAuth, OAuth2Settings, SMTPWrapper, XOAUTH2Auth, resolve_authentication

auth = AppPasswordAuth("you@gmail.com", "abcd efgh ijkl mnop")
auth = XOAUTH2Auth(OAuth2Settings(user="you@gmail.com", client_id="...", client_secret="...", refresh_token="..."))
auth = resolve_authentication()   # 設定檔或環境變數裡的登入方式，沒有則為 None

with SMTPWrapper() as smtp:
    auth.login(smtp)              # 同一個呼叫也能登入 IMAPWrapper
```

`auth.login(client)` 登入 SMTP 或 IMAP wrapper，`auth.authorization()` 回傳 HTTP `Authorization` 標頭的值。
某個機制做不到其中一項時會引發 `MailThunderAuthenticationException`；`MailThunderOAuth2Exception` 現在是它的子類別。
`settings` 是 `OAuth2Settings`；權杖來自共用的權杖快取，並在到期前一分鐘更新。`resolve_authentication()` 與 wrapper
一樣，有 OAuth2 設定時優先於密碼。密碼與權杖不會出現在 `repr` 中。把它交給 `Mail(auth=...)` 或
`MailAccount(auth=...)` 就能用它登入。

---

## 附件政策

`AttachmentPolicy` 定義一封郵件可以攜帶什麼。`validate_attachments` 會在寄出任何東西之前依政策檢查郵件的附件，
並在第一條被違反的規則處引發結構化例外。

```python
from je_mail_thunder import Attachment, AttachmentPolicy, validate_attachments

policy = AttachmentPolicy(
    max_file_size=10 * 1024 * 1024,     # 單一附件的位元組上限
    max_total_size=20 * 1024 * 1024,    # 所有附件合計的位元組上限
    max_count=5,
    allowed_extensions={"pdf", "csv", "html"},
    allowed_mime_types={"application/pdf", "text/*"},
)
attachments = [Attachment.from_path("report.pdf"), Attachment.from_path("results.csv")]
total_bytes = validate_attachments(attachments, policy)
```

每個上限都是選用的：預設值 `None` 表示不設限。副檔名比對不分大小寫、有沒有點都可以，並以最後一個副檔名為準
（`report.pdf.exe` 是 `.exe`）。MIME 類型可以用 `/*` 結尾。
`DEFAULT_ATTACHMENT_POLICY` 允許單一附件與整封郵件各 25 MiB、任何類型。

檢查順序為：數量 → 是否存在 → 大小 → 副檔名 → MIME 類型 → 合計大小：

| 例外 | 引發時機 | 屬性 |
|---|---|---|
| `AttachmentCountExceeded` | 附件數量超過 `max_count` | `count`、`limit` |
| `AttachmentNotFound` | 要附加的檔案不存在 | `path` |
| `AttachmentTooLarge` | 單一附件超過 `max_file_size` | `filename`、`size`、`limit` |
| `AttachmentTypeNotAllowed` | 副檔名或 MIME 類型不在允許範圍內 | `filename`、`kind`、`value` |
| `TotalAttachmentSizeExceeded` | 附件合計超過 `max_total_size` | `size`、`limit` |

它們都繼承自 `MailThunderAttachmentException`（`je_mail_thunder.utils.exception.exceptions`）。類型檢查看的是檔名而不是
內容：它能防止誤寄錯誤的檔案，無法防止刻意改名的檔案。

`Attachment.save(directory)` 用來寫入隨郵件收到的附件。檔名會先處理成安全的名稱：目錄部分、`..`、控制字元與
Windows 不接受的字元都會被移除，因此檔案不會落在 `directory` 之外。

`Mail` 會在每次 `send` 與 `create_draft` 時套用它的政策。SMTP wrapper 的 `create_message_with_attach_and_send`
會依 wrapper 的 `attachment_policy` 檢查檔案（預設為 `DEFAULT_ATTACHMENT_POLICY`；可以指定另一個政策，或設為 `None`
關閉檢查）：被拒絕的檔案會寫入日誌，郵件不會寄出。

---

## 郵件模板

郵件模板包含主旨、純文字內文與 HTML 內文，三者共用同一份 context，所以報表郵件只要寫一次，就能帶入不同的數字寄出：

```python
from je_mail_thunder import Mail

with Mail() as mail:
    mail.send(
        to="qa@example.com",
        template="test_report",
        context={"project": "APITestka", "passed": 98, "failed": 2, "failures": [{"name": "login"}]},
    )
```

`Mail` 以名稱尋找模板：先找專案的 `mail/templates/` 目錄，再找共用目錄（`~/.je_mail_thunder/templates`，或
`$MAIL_THUNDER_TEMPLATE_DIR`）。模板可以是一個 JSON 檔 `test_report.json`（`subject` / `text` / `html` / `variables` /
`metadata`），也可以是一個目錄：

```
mail/templates/test_report/
  subject.txt      [{{ project }}] {{ passed }} passed, {{ failed }} failed
  body.txt         plain-text body
  body.html        HTML body (values are HTML-escaped)
  template.json    {"variables": {"project": {}, "failed": {"default": 0}}, "metadata": {"owner": "qa"}}
```

語法是 Jinja2 中郵件用得到的部分，以標準函式庫實作：

| 語法 | 意義 |
|---|---|
| `{{ user.name }}` | 一個值；以點號取得 dict、list（`items.0`）與公開屬性的內容 |
| `{{ name \| upper }}` | 過濾器：`upper`、`lower`、`title`、`trim`、`length`、`join(", ")`、`default("x")`、`safe` |
| `{% if failed > 0 %} … {% elif skipped %} … {% else %} … {% endif %}` | 條件：一個值、`not`，或一次比較（`== != < <= > >=`） |
| `{% for test in failures %} {{ loop.index }}. {{ test.name }} {% endfor %}` | 迴圈，可用 `loop.index`、`loop.first`、`loop.last`、`loop.length` |
| `{# note #}` | 註解 |

模板只能讀取 context：其中沒有任何內容會被當成 Python 執行，HTML 內文中的每個值都會做 HTML 跳脫，除非經過 `safe`。
在 `variables` 宣告的變數會在產生內容之前檢查，`TemplateContextError.missing` 會列出所有缺少的變數；有 `default` 的變數
是選用的。`mail.render("test_report", context)` 回傳產生出來的主旨、純文字與 HTML，不會寄出；與 `template=` 同時給的
欄位（例如 `subject=`）優先於模板產生的結果。錯誤都是 `MailThunderTemplateException` 的子類別：`TemplateNotFound`、
`TemplateSyntaxError`、`TemplateContextError`、`TemplateRenderError`。

模板也可以在程式中建立：`mail.templates.add(MailTemplate("welcome", subject="Hi {{ name }}", text="..."))`。

---

## 郵件事件與觸發器

`Mail` 會把郵件發生的事情以事件回報，不論供應商是哪一家都用同一套名稱；觸發器後端則負責監看資料夾，讓新郵件也成為事件：

```python
from je_mail_thunder import Mail

mail = Mail()

def handle_report(event):
    print(event.message.sender, event.message.subject)

mail.on("message_received", handle_report, filter={"subject": "[TEST]", "has_attachments": True})
mail.watch("INBOX")                  # 在背景執行緒每 60 秒查看一次
mail.watch("INBOX", idle=True)       # 或由伺服器通知新郵件（IMAP IDLE）

@mail.on("message_failed")           # on() 也可以當作裝飾器
def alert(event):
    print("not sent:", event.error)
```

| 事件 | 發生時機 |
|---|---|
| `message_received`、`attachment_received` | 被監看的資料夾有新郵件（它的每個附件各一次） |
| `message_sent` | `send` 已把郵件交給供應商 |
| `message_failed` | `send` 或 `create_draft` 失敗，不論原因 |
| `attachment_rejected` | 附件不存在或違反附件政策 |
| `authentication_failed`、`connection_failed` | 沒有認證資訊或登入被拒；無法連上伺服器或連線中斷 |

處理函式會收到一個 `MailEvent`（`name`、`message`、`attachment`、`error`、`provider`、`folder`、`timestamp`、`metadata`）。
`filter` 可以是規則的 mapping（`sender`、`recipient`、`subject`、`body`、`has_attachments`、`attachment_type`、`since`、
`until`、`metadata`）、接收事件的函式，或 `MailFilter`；文字規則不分大小寫，也可以使用編譯過的正規表示式。
失敗仍然會以例外回報給呼叫端；處理函式引發的例外只會被記錄，不會中斷其他事情。

`mail.watch(folder, interval=60, idle=False, start=True, include_existing=False)` 會在 `mail.triggers` 加入一個後端：
`IMAPPollingBackend`（只搜尋比上次看到的更大的 UID）、`IMAPIdleBackend`，或是適用於其他 `MailStore` 的 `PollingBackend`。
監看使用自己的連線，第一次查看只會記下已經存在的郵件；`mail.triggers.poll()` 則是只查看一次，不啟動執行緒。
在動作檔中，`MT_mail_poll` 會回傳上一次 `MT_mail_poll` 以來的事件。

---

## Microsoft Graph

`microsoft_graph` 供應商透過 Microsoft Graph API 存取 Microsoft 365 信箱，而不是 SMTP 與 IMAP。`Mail` 的呼叫方式完全相同，
只有供應商名稱不同：

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

- **如何選用**：在程式中使用 `Mail(provider="microsoft_graph")`。對 `Mail()` 與 `MT_mail_*` 指令，則在
  `mail_thunder_content.json` 設定 `"mail_provider": "microsoft_graph"`，或設定環境變數 `mail_thunder_mail_provider`
  （它可以是任何已註冊的供應商）。`microsoft` 仍然代表 SMTP 與 IMAP。
- **登入**：只能用 OAuth2。應用程式註冊需要委派權限 `Mail.Send` 與 `Mail.ReadWrite`。OAuth2 設定沒有指定 `scope` 時，
  會以 Graph 的 scope 取得權杖。
- **寄送**：附件不大時是一次 `sendMail` 請求；否則先建立草稿，把每個附件加上去（超過 3 MiB 的走 upload session），
  再把草稿寄出。
- **讀取**：資料夾可以是 `INBOX`、`Drafts`、`Sent`、`Deleted Items`、`Junk`、`Archive` 或顯示名稱；`query=` 是 OData 的
  `$filter` 運算式，例如 `from/emailAddress/address eq 'ci@example.com'`。
- **與 SMTP 的差異**：郵件只有一個內文（兩者都給時使用 HTML）、自訂標頭必須以 `X-` 開頭、`sender` 若不是帳號本人
  需要「以…身分傳送」權限。
- **觸發器**：`mail.watch()` 會使用 `GraphPollingBackend`。`GraphWebhookBackend(provider, "https://your.host/hook")`
  讓 Graph 主動通知新郵件：它的監聽器綁定 `localhost:9946`，放在你的 HTTPS 代理之後，會回應 Graph 的驗證，
  並忽略沒有帶著密鑰的通知。

請求只會送往 `https://graph.microsoft.com`；權杖被拒絕時會引發 `MailThunderAuthenticationException`。

---

## 監控

三種監聽者把[郵件事件](#郵件事件與觸發器)變成事後可以查看的資料。它們都掛在 `mail.events` 上，而且都不會讓郵件停下來：

```python
from je_mail_thunder import AuditLog, Mail, ProviderHealth, WebhookForwarder

mail = Mail()
audit, health = AuditLog(), ProviderHealth()
audit.attach(mail.events)                 # 每個事件一行 JSON，寫入 ~/.je_mail_thunder/audit/mail_audit.jsonl
health.attach(mail.events)                # 每個供應商的 healthy / degraded / down 狀態
mail.on("*", WebhookForwarder("https://hooks.example.com/mail", secret="shared-secret"))

print(health.report())                    # [{"provider": "smtp", "state": "healthy", ...}]
print(health.probe(mail.providers))       # 立刻要求每個供應商連線並登入
print(audit.entries(limit=10))
```

- **`AuditLog(path=None, subjects=True)`** 記錄誰在什麼時候寄出或收到了什麼：位址、主旨、附件名稱與大小、供應商，
  以及失敗時的錯誤。不會記錄內文、附件內容或任何認證資訊。檔案只會附加（可用 `MAIL_THUNDER_AUDIT_FILE` 改變位置），
  超過 10 MiB 時會輪替。
- **`ProviderHealth(failure_threshold=3)`** 在成功後是 `healthy`，失敗後是 `degraded`，連續失敗 `failure_threshold` 次後
  是 `down`。只有供應商本身的失敗才會計入（登入被拒、連線中斷、郵件被拒絕），缺少收件者或附件被拒絕不算。
  `probe` 會呼叫每個供應商的 `check()`。
- **`WebhookForwarder(url, secret=None, bodies=False)`** 透過背景佇列把每個事件以 JSON POST 到一個 `https` 位址，
  所以接收端再慢也不會拖慢 `send`。有 `secret` 時，每個請求都帶有
  `X-MailThunder-Signature: sha256=<內容的 HMAC-SHA256>`。除非 `bodies=True`，否則不包含郵件內文。

---

## 專案郵件層

自動化專案把「怎麼寄信」放在自己的 `mail/` 目錄裡，程式只要取得一個設定好的 `Mail`，不必指定供應商。之後要把專案
換到另一家供應商，或是不寄出任何東西先試跑，都只需要修改一個檔案：

```
MyProject/
  mail/
    config.py       # PROVIDER, AUTH or ACCOUNT, ATTACHMENT_POLICY, AUDIT (all optional)
    triggers.py     # register(mail): event handlers and watched folders
    templates/      # the project's mail templates
```

```python
from je_mail_thunder import project_mail

mail = project_mail()                    # 工作目錄中的專案
mail.send(to="qa@example.com", template="test_report",
          context={"project": "MyProject", "passed": 98, "failed": 2})
mail.triggers.poll()                     # 查看一次有沒有新郵件
mail.close()
```

- **`config.py`** 可以設定 `PROVIDER`（已註冊的供應商名稱）、`AUTH` 或完整的 `ACCOUNT`、`ATTACHMENT_POLICY`，以及 `AUDIT`
  （`True` 會把每個郵件事件記錄到 `mail/audit.jsonl`）。省略 `AUTH` 時登入資訊來自 `mail_thunder_content.json` 或
  環境變數，這樣認證資訊就不會出現在專案的檔案裡。
- **`triggers.py`** 定義 `register(mail)`，負責訂閱專案的處理函式（`mail.on(...)`）並指定要監看的資料夾（`mail.watch(...)`）。
- **`templates/`** 會比共用模板先被搜尋。

`create_project_dir()` 會建立這一層，內含 `test_report` 模板並使用 `file` 供應商，所以新專案在指定真正的供應商之前，
郵件都只會留在磁碟上。`project_mail()` 會執行 `config.py` 與 `triggers.py`，它們是專案的 Python 檔：只載入你信任的專案。
沒有任何動作指令會載入這一層；`describe_mail_layer()` 則只列出檔案，不會執行它們。

---

## MailThunder Studio

MailThunder Studio 是一個在本機開啟的頁面，用來查看並試用郵件 API 目前的設定。它由標準函式庫提供服務、不需要額外的
套件，而且只會呼叫[核心郵件 API](#核心郵件-api)，所以不論使用哪一家供應商都一樣運作：

```bash
python -m je_mail_thunder.studio                       # 使用設定檔或環境變數裡的帳號
python -m je_mail_thunder.studio --project MyProject   # 使用某個專案的郵件層（會執行它的 mail/config.py 與 mail/triggers.py）
python -m je_mail_thunder.studio --port 9950 --no-browser
```

它會印出像 `http://localhost:9947/#token=...` 這樣的位址並開啟它。頁面有 English 與中文兩種語言。

| 頁面 | 顯示與可執行的內容 |
|---|---|
| 儀表板 | 帳號（絕不顯示密碼或權杖）、每個供應商的健康狀態、各項數量、最新的稽核紀錄，以及一個可以寄信的表單 |
| 帳號 | 帳號與其伺服器、已註冊的供應商，以及要求每個供應商連線並登入的按鈕 |
| 模板 | 每個模板與其變數；輸入 JSON 格式的 context 就能產生內容，不會寄出 |
| 觸發器 | 事件、已訂閱的處理函式與過濾條件、觸發器後端，以及立即查看一次新郵件的按鈕 |
| 政策 | 附件政策，可以修改，變更在 Studio 執行期間有效 |
| 專案 | 專案郵件層的檔案與模板；不會執行其中任何檔案 |
| 日誌 | 日誌檔的結尾與稽核日誌 |
| 設定 | MailThunder 存放檔案的位置、已註冊的供應商，以及執行環境的版本 |

Studio 是給坐在這台電腦前的人使用的工具。它只綁定 `localhost`；每個 API 請求都需要該次執行的隨機權杖，權杖放在位址的
fragment 裡，瀏覽器不會把它送給任何伺服器；`Host` 不同的請求會被拒絕；頁面不會從其他地方載入任何東西，所有內容都以
文字寫入，所以透過郵件送來的內容無法在瀏覽器中執行；任何回應都不包含密碼或權杖；從頁面寄出的郵件也不能指定附件。
不使用時請把它停掉。`je_mail_thunder.studio.server` 的 `start_studio(mail)` 可以從 Python 啟動它。

---

## 腳本引擎

MailThunder 內建 JSON 腳本引擎，讓你無需撰寫 Python 程式碼即可自動化郵件工作流程。

### Action JSON 格式

動作檔使用指令列表格式。每個指令為一個陣列，第一個元素為指令名稱，可選的第二個元素為參數：

```json
{
  "mail_thunder": [
    ["指令名稱"],
    ["指令名稱", {"key": "value"}],
    ["指令名稱", ["arg1", "arg2"]]
  ]
}
```

- 使用 **dict** `{}` 作為第二個元素傳遞關鍵字參數（`**kwargs`）
- 使用 **list** `[]` 作為第二個元素傳遞位置參數（`*args`）
- 只寫指令名稱（不含第二個元素）表示無參數指令

### 可用的腳本指令

| 指令 | 說明 | 參數 |
|------|------|------|
| `MT_smtp_later_init` | 初始化並登入 SMTP | 無 |
| `MT_smtp_create_message_and_send` | 建立並寄送郵件 | `{"message_content": str, "message_setting_dict": dict}` |
| `MT_smtp_create_message_with_attach_and_send` | 建立並寄送帶附件的郵件 | `{"message_content": str, "message_setting_dict": dict, "attach_file": str, "use_html": bool}` |
| `MT_smtp_quit` | 中斷 SMTP 連線（舊名 `smtp_quit` 仍可用） | 無 |
| `MT_imap_later_init` | 初始化並登入 IMAP | 無 |
| `MT_imap_select_mailbox` | 選擇信箱 | `{"mailbox": str, "readonly": bool}`（預設：INBOX）|
| `MT_imap_search_mailbox` | 搜尋並取得郵件詳細資訊 | `{"search_str": str, "charset": str}` |
| `MT_imap_mail_content_list` | 取得所有郵件內容列表 | `{"search_str": str, "charset": str}` |
| `MT_imap_output_all_mail_as_file` | 匯出所有郵件為檔案 | `{"search_str": str, "charset": str}` |
| `MT_imap_quit` | 中斷 IMAP 連線 | 無 |
| `MT_mail_send` | 透過設定的供應商寄送郵件 | `{"to": str 或 list, "subject": str, "text": str, "html": str, "cc": ..., "bcc": ..., "attachments": [路徑], "sender": str, "reply_to": ..., "headers": dict}` |
| `MT_mail_create_draft` | 將郵件存成草稿 | `MT_mail_send` 的參數，另加 `"folder": str` |
| `MT_mail_get_messages` | 取得資料夾的郵件，最新的在前 | `{"folder": str, "limit": int, "unread_only": bool, "query": str}`（預設：INBOX、不限數量） |
| `MT_mail_get_message` | 依識別碼取得一封郵件 | `{"message_id": str, "folder": str}` |
| `MT_mail_delete_message` | 依識別碼刪除一封郵件 | `{"message_id": str, "folder": str}` |
| `MT_mail_close` | 關閉供應商的連線 | 無 |
| `MT_mail_render_template` | 產生郵件模板的內容，不寄出 | `{"template": str, "context": dict}` |
| `MT_mail_poll` | 取得資料夾自上次輪詢以來新郵件的事件 | `{"folder": str}`（預設：INBOX） |
| `MT_set_mail_thunder_os_environ` | 設定驗證環境變數 | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | 取得驗證環境變數 | 無 |
| `MT_add_package_to_executor` | 載入 Python 套件至執行器 | `["套件名稱"]` |

`MT_mail_*` 指令在 `mail_instance` 上使用[核心郵件 API](#核心郵件-api)；`mail_instance` 是一個使用設定檔或環境變數
帳號的 `Mail()`。這些指令在第一次使用時才連線，並回傳可轉成 JSON 的值。它的附件政策只能從 Python 設定
（`mail_instance.policy = AttachmentPolicy(...)`），不能由動作設定，所以動作檔無法放寬它。

**範例 — 透過核心郵件 API 寄送郵件並讀取收件匣：**

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

**範例 — 透過 JSON 腳本寄送郵件：**

```json
{
  "mail_thunder": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "自動化郵件",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["MT_smtp_quit"]
  ]
}
```

**範例 — 讀取並匯出所有郵件：**

```json
{
  "mail_thunder": [
    ["MT_imap_later_init"],
    ["MT_imap_select_mailbox"],
    ["MT_imap_output_all_mail_as_file"]
  ]
}
```

### 擴充自訂指令

你可以將自己的函式加入腳本執行器：

```python
from je_mail_thunder import add_command_to_executor

def my_custom_function(param1, param2):
    print(f"自訂指令: {param1}, {param2}")

add_command_to_executor({"my_command": my_custom_function})
```

之後即可在 JSON 動作檔中使用 `"my_command"`。

### 動態載入套件

在執行時動態載入任何已安裝的 Python 套件至執行器：

```json
{
  "mail_thunder": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

這會載入指定套件的所有函式、內建功能和類別，並以 `套件名稱_` 為前綴。

**套件閘門。** `MT_add_package_to_executor` 能載入 `os` 或 `subprocess`，所以只要 action 檔或 socket 用戶端寫得出
這些名字，就能執行任何東西。哪些套件可以載入，由宿主程式決定：

```python
from je_mail_thunder.utils.executor.action_executor import executor

executor.allow_packages("json")                # 這些套件與其子模組
executor.set_allow_arbitrary_packages(False)   # 其他套件在匯入前就拒絕
```

這兩個開關都不是 action 命令，所以 action 檔不能自己打開閘門。被拒絕的套件會以 `ExecuteActionException`
記錄在該動作的結果裡。宿主程式呼叫任一個開關之前，任何套件仍會載入，但會發出 `DeprecationWarning`：之後的版本會
預設拒絕清單以外的套件。

> **警告：** 將 `os` 等套件載入執行器可能存在安全風險。請僅載入可信任的套件並驗證所有輸入。

---

## 專案模板

MailThunder 可以快速建立包含預設模板的專案：

```python
from je_mail_thunder import create_project_dir

create_project_dir()  # 在目前目錄建立
# 或
create_project_dir(project_path="/path/to/project", parent_name="MyMailProject")
```

建立的目錄結構如下：

```
MyMailProject/
  keyword/
    keyword1.json      # SMTP 寄送郵件模板
    keyword2.json      # IMAP 讀取並匯出模板
    bad_keyword_1.json # 套件載入範例（安全性警告）
  executor/
    executor_one_file.py   # 執行單一動作檔
    executor_folder.py     # 執行目錄內所有動作檔
    executor_bad_file.py   # 不良實踐範例
  mail/
    config.py              # 專案的供應商、附件政策與稽核日誌
    triggers.py            # register(mail)：事件處理函式與要監看的資料夾
    templates/test_report/ # subject.txt、body.txt、body.html、template.json
```

---

## 命令列介面

MailThunder 透過 `python -m je_mail_thunder` 提供命令列介面：

```bash
# 執行單一 JSON 動作檔
python -m je_mail_thunder -e /path/to/action.json

# 執行目錄內所有 JSON 動作檔
python -m je_mail_thunder -d /path/to/actions/

# 直接執行 JSON 字串
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["MT_smtp_quit"]]'

# 建立包含模板的新專案
python -m je_mail_thunder -c /path/to/project
```

| 旗標 | 完整旗標 | 說明 |
|------|----------|------|
| `-e` | `--execute_file` | 執行單一 JSON 動作檔 |
| `-d` | `--execute_dir` | 執行目錄內所有 JSON 動作檔 |
| `-c` | `--create_project` | 建立包含模板的專案 |
| | `--execute_str` | 直接執行 JSON 字串 |

---

## Socket 伺服器

MailThunder 內建 TCP Socket 伺服器，可接收遠端 JSON 指令：

```python
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_mail_thunder_socket_server

server = start_mail_thunder_socket_server(host="localhost", port=9942)
# 伺服器現在在背景執行緒中運行
```

**向伺服器傳送指令：**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9942))

# 傳送動作指令
command = json.dumps([["MT_smtp_later_init"], ["MT_smtp_quit"]])
client.send(command.encode("utf-8"))

# 接收回應
response = client.recv(8192).decode("utf-8")
print(response)

client.close()
```

傳送 `"quit_server"` 可關閉伺服器。

---

## API 參考

### Mail

`Mail(provider=None, auth=None, account=None, policy=None, providers=None)`：與供應商無關的 API。可作為
context manager；第一次呼叫之前不會連線。

| 方法 | 說明 |
|------|------|
| `send(message=None, **fields)` | 檢查並寄送 `MailMessage`，或由 `fields` 建立的郵件；回傳該郵件 |
| `create_draft(message=None, folder=None, **fields)` | 檢查郵件並存成草稿；回傳其識別碼，或 `None` |
| `get_messages(folder="INBOX", limit=None, unread_only=False, query=None)` | 迭代資料夾的郵件，最新的在前 |
| `get_message(message_id, folder="INBOX")` | 回傳一封郵件 |
| `delete_message(message_id, folder="INBOX")` | 刪除一封郵件 |
| `close()` | 關閉連線；下一次呼叫會重新連線 |

| 名稱 | 說明 |
|------|------|
| `MailMessage(subject, to, cc, bcc, sender, reply_to, text, html, attachments, headers, message_id, date)` | 與供應商無關的郵件；`to_dict()` 回傳可轉成 JSON 的值 |
| `MailAccount(provider="google", auth=None, servers=None)` / `MailServers(smtp_host, smtp_port, smtp_starttls, imap_host, drafts_folder)` | 誰的郵件、在哪些伺服器上、用哪種方式登入 |
| `MailSender` / `MailStore` / `register_provider(name, factory)` | 供應商介面與註冊表；`SMTPProvider` 與 `IMAPProvider` 實作了它們 |
| `mail_instance` | `MT_mail_*` 指令使用的 `Mail()` |
| `legacy_message(...)` / `mail_from_wrappers(smtp=None, imap=None, policy=None)` | 從 wrapper API 過渡的橋接函式 |

### SMTPWrapper

繼承自 `smtplib.SMTP_SSL`（經由 `SMTPClientMixin`）。預設主機：`smtp.gmail.com`，預設埠號：`465`。

| 方法 | 說明 |
|------|------|
| `later_init()` | 使用設定檔或環境變數登入（有 OAuth2 設定時用 OAuth2） |
| `create_message(message_content, message_setting_dict, **kwargs)` | 建立 `EmailMessage` 物件 |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | 建立帶附件的 `MIMEMultipart` 訊息 |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | 建立並立即寄送郵件 |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | 建立並寄送帶附件的郵件 |
| `try_to_login_with_env_or_content()` | 嘗試從設定檔或環境變數登入（先 OAuth2 設定，再帳號密碼），回傳 `bool` |
| `oauth2_login(user, access_token)` | 以 SASL `XOAUTH2` 登入；被拒時拋出 `smtplib.SMTPAuthenticationError` |
| `quit()` | 中斷連線並關閉 |

**使用其他 SMTP 服務商：**

```python
from je_mail_thunder import SMTPStartTLSWrapper, SMTPWrapper

# 其他主機的隱含式 TLS
smtp = SMTPWrapper(host="smtp.example.com", port=465)
# STARTTLS，例如 Microsoft 365（預設即 smtp.office365.com:587）
smtp = SMTPStartTLSWrapper()
```

### SMTPStartTLSWrapper

繼承自 `smtplib.SMTP`，方法與 `SMTPWrapper` 相同（兩者都混入 `SMTPClientMixin`）。預設主機：`smtp.office365.com`，
預設埠號：`587`。它在送出任何其他內容前先以 `STARTTLS` 升級連線（驗證憑證與主機名稱），並拒絕不提供 `STARTTLS` 的
伺服器：關閉連線並拋出 `smtplib.SMTPNotSupportedError`。

### IMAPWrapper

繼承自 `imaplib.IMAP4_SSL`。預設主機：`imap.gmail.com`。

| 方法 | 說明 |
|------|------|
| `later_init()` | 使用設定檔或環境變數登入（有 OAuth2 設定時用 OAuth2） |
| `select_mailbox(mailbox="INBOX", readonly=False)` | 選擇信箱，回傳 `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | 搜尋並回傳原始郵件詳細資訊列表 |
| `mail_content_list(search_str="ALL", charset=None)` | 回傳已解析的郵件內容字典列表 |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主旨為檔名匯出所有郵件；路徑分隔符號、控制字元與 `: * ? " < > \|` 會被換成 `_` |
| `oauth2_login(user, access_token)` | 以 SASL `XOAUTH2` 登入；被拒時拋出 `imaplib.IMAP4.error` |
| `quit()` | 關閉信箱並登出 |

**郵件內容字典格式：**

```python
{
    "SUBJECT": "郵件主旨",
    "FROM": "sender@example.com",
    "TO": "receiver@example.com",
    "BODY": "郵件內容..."
}
```

### Executor 函式

| 函式 | 說明 |
|------|------|
| `execute_action(action_list)` | 執行動作指令列表 |
| `execute_files(execute_files_list)` | 執行多個 JSON 動作檔 |
| `add_command_to_executor(command_dict)` | 將自訂函式加入執行器 |
| `read_action_json(file_path)` | 讀取 JSON 動作檔 |

### 工具函式

| 函式 | 說明 |
|------|------|
| `create_project_dir(project_path, parent_name)` | 建立包含模板的專案 |
| `set_mail_thunder_os_environ(mail_thunder_user, mail_thunder_user_password)` | 設定驗證環境變數 |
| `get_mail_thunder_os_environ()` | 取得驗證環境變數 |
| `read_output_content()` | 從目前工作目錄讀取 `mail_thunder_content.json` |
| `write_output_content()` | 將內容資料寫入 `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | 取得目錄內所有檔案列表 |
| `OAuth2Settings(user, provider="google", client_id=None, client_secret=None, refresh_token=None, access_token=None, tenant="common", token_url=None, scope=None)` | OAuth2 登入設定；`OAUTH2_PROVIDERS` 有 `google` 與 `microsoft` 預設 |
| `oauth2_token_cache.access_token(settings)` | 快取的存取權杖，快到期時更新（`refresh_access_token(settings)` 每次都向端點要） |
| `resolve_oauth2_settings()` | 從設定檔或環境變數取得 OAuth2 設定，沒有則為 `None` |
| `xoauth2_string(user, access_token)` | SASL `XOAUTH2` 的初始回應 |

---

## 專案結構

```
MailThunder/
  je_mail_thunder/
    __init__.py              # 公開 API 匯出
    __main__.py              # CLI 進入點
    attachments/             # 附件模型、AttachmentPolicy 與驗證器
    auth/                    # 驗證機制：密碼、應用程式密碼、OAuth2、XOAUTH2
    core/                    # Mail（與供應商無關的 API）、MailMessage、MailAccount
    providers/               # MailSender / MailStore 介面、SMTPProvider、IMAPProvider、註冊表
    templates/               # 郵件模板：模板語法、MailTemplate、TemplateLoader
    triggers/                # 郵件事件：過濾器、dispatcher、輪詢與 IMAP IDLE 後端
    monitoring/              # AuditLog 與 ProviderHealth，由郵件事件驅動
    studio/                  # MailThunder Studio：本機頁面、它的 API 與 HTTP 伺服器
    smtp/
      smtp_wrapper.py        # SMTPClientMixin、SMTPWrapper、SMTPStartTLSWrapper
    imap/
      imap_wrapper.py        # IMAPWrapper 類別
    utils/
      exception/             # 自訂例外與錯誤標籤
      executor/              # JSON 腳本引擎
      file_process/          # 檔案工具函式
      json/                  # JSON 檔案讀寫
      json_format/           # JSON 格式化
      lazy_instance/         # 首次使用時才連線的惰性客戶端
      logging/               # 日誌實例
      oauth2/                # OAuth2 設定、權杖更新、XOAUTH2
      package_manager/       # 動態套件載入器
      project/               # 專案模板建立
      save_mail_user_content/ # 驗證設定與環境變數處理
      socket_server/         # TCP Socket 伺服器
  test/                      # 單元測試
  docs/                      # Sphinx 文件
```

---

## 授權條款

本專案採用 [MIT 授權條款](../LICENSE)。
