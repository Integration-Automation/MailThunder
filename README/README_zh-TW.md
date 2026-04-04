# MailThunder

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
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
  - [IMAPWrapper](#imapwrapper)
  - [Executor 函式](#executor-函式)
  - [工具函式](#工具函式)
- [專案結構](#專案結構)
- [授權條款](#授權條款)

---

## 功能特色

- **SMTP 支援** — 透過 SSL 寄送郵件，預設使用 Gmail，也可自訂其他 SMTP 服務
- **IMAP4 支援** — 透過 IMAP4 SSL 讀取、搜尋和匯出郵件
- **附件處理** — 自動偵測文字、圖片、音訊和二進位檔案的 MIME 類型
- **HTML 郵件** — 支援寄送 HTML 格式的郵件與附件
- **JSON 腳本引擎** — 使用 JSON 動作檔自動化郵件工作流程
- **專案模板** — 快速建立包含預設關鍵字和執行器模板的專案
- **Socket 伺服器** — 透過 TCP Socket 遠端控制 MailThunder
- **套件管理器** — 動態載入 Python 套件至腳本執行器
- **環境變數驗證** — 支援設定檔或作業系統環境變數進行身份驗證
- **自動匯出** — 一行指令即可將信箱所有郵件匯出為本機檔案
- **Context Manager 支援** — SMTP 和 IMAP 連線皆可使用 `with` 語法
- **日誌記錄** — 內建所有操作的日誌紀錄

---

## 系統需求

- Python 3.9 或更新版本

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

MailThunder 支援兩種身份驗證方式。它會先嘗試 JSON 設定檔，若找不到則回退至環境變數。

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

---

## 腳本引擎

MailThunder 內建 JSON 腳本引擎，讓你無需撰寫 Python 程式碼即可自動化郵件工作流程。

### Action JSON 格式

動作檔使用指令列表格式。每個指令為一個陣列，第一個元素為指令名稱，可選的第二個元素為參數：

```json
{
  "auto_control": [
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
| `smtp_quit` | 中斷 SMTP 連線 | 無 |
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
  "auto_control": [
    ["MT_smtp_later_init"],
    ["MT_smtp_create_message_and_send", {
      "message_content": "Hello World!",
      "message_setting_dict": {
        "Subject": "自動化郵件",
        "To": "receiver@gmail.com",
        "From": "sender@gmail.com"
      }
    }],
    ["smtp_quit"]
  ]
}
```

**範例 — 讀取並匯出所有郵件：**

```json
{
  "auto_control": [
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
  "auto_control": [
    ["MT_add_package_to_executor", ["os"]],
    ["os_system", ["echo Hello from os.system"]]
  ]
}
```

這會載入指定套件的所有函式、內建功能和類別，並以 `套件名稱_` 為前綴。

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
python -m je_mail_thunder --execute_str '[["MT_smtp_later_init"], ["smtp_quit"]]'

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
from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import start_autocontrol_socket_server

server = start_autocontrol_socket_server(host="localhost", port=9944)
# 伺服器現在在背景執行緒中運行
```

**向伺服器傳送指令：**

```python
import socket
import json

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 9944))

# 傳送動作指令
command = json.dumps([["MT_smtp_later_init"], ["smtp_quit"]])
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

繼承自 `smtplib.SMTP_SSL`。預設主機：`smtp.gmail.com`，預設埠號：`465`。

| 方法 | 說明 |
|------|------|
| `later_init()` | 使用設定檔或環境變數登入 |
| `create_message(message_content, message_setting_dict, **kwargs)` | 建立 `EmailMessage` 物件 |
| `create_message_with_attach(message_content, message_setting_dict, attach_file, use_html=False)` | 建立帶附件的 `MIMEMultipart` 訊息 |
| `create_message_and_send(message_content, message_setting_dict, **kwargs)` | 建立並立即寄送郵件 |
| `create_message_with_attach_and_send(message_content, message_setting_dict, attach_file, use_html=False)` | 建立並寄送帶附件的郵件 |
| `try_to_login_with_env_or_content()` | 嘗試從設定檔或環境變數登入，回傳 `bool` |
| `quit()` | 中斷連線並關閉 |

**使用其他 SMTP 服務商：**

```python
from je_mail_thunder import SMTPWrapper

# 範例：Outlook
smtp = SMTPWrapper(host="smtp.office365.com", port=587)
```

### IMAPWrapper

繼承自 `imaplib.IMAP4_SSL`。預設主機：`imap.gmail.com`。

| 方法 | 說明 |
|------|------|
| `later_init()` | 使用設定檔或環境變數登入 |
| `select_mailbox(mailbox="INBOX", readonly=False)` | 選擇信箱，回傳 `bool` |
| `search_mailbox(search_str="ALL", charset=None)` | 搜尋並回傳原始郵件詳細資訊列表 |
| `mail_content_list(search_str="ALL", charset=None)` | 回傳已解析的郵件內容字典列表 |
| `output_all_mail_as_file(search_str="ALL", charset=None)` | 以主旨為檔名匯出所有郵件 |
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
| `set_mail_thunder_os_environ(user, password)` | 設定驗證環境變數 |
| `get_mail_thunder_os_environ()` | 取得驗證環境變數 |
| `read_output_content()` | 從目前工作目錄讀取 `mail_thunder_content.json` |
| `write_output_content()` | 將內容資料寫入 `mail_thunder_content.json` |
| `get_dir_files_as_list(path)` | 取得目錄內所有檔案列表 |

---

## 專案結構

```
MailThunder/
  je_mail_thunder/
    __init__.py              # 公開 API 匯出
    __main__.py              # CLI 進入點
    smtp/
      smtp_wrapper.py        # SMTPWrapper 類別
    imap/
      imap_wrapper.py        # IMAPWrapper 類別
    utils/
      exception/             # 自訂例外與錯誤標籤
      executor/              # JSON 腳本引擎
      file_process/          # 檔案工具函式
      json/                  # JSON 檔案讀寫
      json_format/           # JSON 格式化
      logging/               # 日誌實例
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

Copyright (c) 2021 JE-Chen
