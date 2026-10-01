# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/je_mail_thunder)](https://pypi.org/project/je-mail-thunder/)

**MailThunder** 是一款輕量且靈活的 Python 電子郵件自動化工具。它封裝了 SMTP 和 IMAP4 協定，提供 JSON 腳本引擎與專案模板功能，讓寄信、收信與管理郵件內容變得輕鬆簡單。

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
- [身份驗證](#身份驗證)
  - [JSON 設定檔](#json-設定檔)
  - [環境變數](#環境變數)
  - [OAuth2（Google 與 Microsoft）](#oauth2google-與-microsoft)
- [腳本引擎](#腳本引擎)
  - [Action JSON 格式](#action-json-格式)
  - [可用的腳本指令](#可用的腳本指令)
  - [擴充自訂指令](#擴充自訂指令)
  - [動態載入套件](#動態載入套件)
- [專案模板](#專案模板)
- [命令列介面](#命令列介面)
- [Socket 伺服器](#socket-伺服器)
- [API 參考](#api-參考)
  - [SMTPWrapper](#smtpwrapper)
  - [SMTPStartTLSWrapper](#smtpstarttlswrapper)
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函式](#executor-函式)
  - [工具函式](#工具函式)
- [專案結構](#專案結構)
- [授權條款](#授權條款)

---

## 功能特色

- **SMTP 支援** — 透過隱含式 TLS 寄送郵件，預設使用 Gmail，也可自訂其他 SMTP 服務；或透過 STARTTLS（Microsoft 365）
- **IMAP4 支援** — 透過 IMAP4 SSL 讀取、搜尋和匯出郵件
- **附件處理** — 自動偵測文字、圖片、音訊和二進位檔案的 MIME 類型
- **HTML 郵件** — 支援寄送 HTML 格式的郵件與附件
- **JSON 腳本引擎** — 使用 JSON 動作檔自動化郵件工作流程
- **專案模板** — 快速建立包含預設關鍵字和執行器模板的專案
- **Socket 伺服器** — 透過 TCP Socket 遠端控制 MailThunder
- **套件管理器** — 動態載入 Python 套件至腳本執行器
- **環境變數驗證** — 支援設定檔或作業系統環境變數進行身份驗證
- **OAuth2 登入** — Gmail 與 Microsoft 365 的 SASL `XOAUTH2`，以標準函式庫交換 refresh token 並快取存取權杖
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
| `MT_set_mail_thunder_os_environ` | 設定驗證環境變數 | `{"mail_thunder_user": str, "mail_thunder_user_password": str}` |
| `MT_get_mail_thunder_os_environ` | 取得驗證環境變數 | 無 |
| `MT_add_package_to_executor` | 載入 Python 套件至執行器 | `["套件名稱"]` |

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
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主旨為檔名匯出所有郵件 |
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
