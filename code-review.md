# 程式審核：MailThunder

## 審核者

- 審核者：工作區程式審核
- 日期：2026-10-22
- 對象：`MailThunder`（套件原始碼 `je_mail_thunder/`）
- 結論：通過

## 審核規範

共通規範在工作區 repo [JE-Chen/Codes](https://github.com/JE-Chen/Codes) 的 `docs/code-review-standard.md`。下面留下 2026-10-22 這次審核所用的條款，讓審核紀錄的依據對得上那一次。之後的審核以工作區那份為準。本專案更嚴的條款仍以本節與本專案的 `CLAUDE.md` 為準。

嚴重度只有三種：缺陷、建議、備註。通過＝沒有未關閉的缺陷；有條件通過＝沒有立即損害；需修正＝有未關閉的缺陷。設計過的 `SAFE_BUILTINS` 與套件閘門白名單，沒有被繞過就不列缺陷。

1. 設計：符合既有分層、包裝器、命令與提供者介面，不另開平行路徑。
2. 可讀性：認知複雜度 ≤ 15、函式 ≤ 80 行、巢狀 ≤ 4、參數 ≤ 7、每行 ≤ 120。本專案更嚴，從嚴：循環複雜度 ≤ 10、函式 ≤ 50 行、類別 ≤ 300 行、模組 ≤ 750 行（`CLAUDE.md` Linter Compliance）。
3. 錯誤處理：不使用裸 `except`；失敗要記錄，並重新拋出或轉成 `MailThunderException` 子類，不可默默吞掉。
4. 死碼：不留註解掉的程式、未使用的相容墊片或沒有問題編號的 TODO。
5. 型別與 docstring：公開模組、類別與函式要有 docstring，`:param` / `:return:` / `:raises:` 必須與行為一致。
6. 安全：憑證不寫死、不寫進日誌；JSON 只註冊白名單內建函式；SMTP/IMAP 不得關掉 TLS 或憑證驗證；套件閘門不可被動作檔自己打開。
7. 測試：這次不執行測試，只看熱點有沒有對應的測試檔存在。
8. 效能先量測：未見新的熱路徑宣稱，不依感覺要求改寫。
9. `architecture.md` §6：跨專案契約（動作鍵、socket 埠、PyBreeze 會匯入的名稱、內建函式政策）不可在未改呼叫端時改名或移除。
10. 文件同步：行為與 `architecture.md`、`CLAUDE.md`、`progress.md`、三份 README 的套件閘門說明一致。

## 審核紀錄

### 方法

工作樹熱點審核，不是逐行審完全部。先讀 `architecture.md`（含 §6、§7）、`CLAUDE.md` 的安全與長度段落，以及 `progress.md` 前 80 行。接著只在 `je_mail_thunder/` 的 `*.py` 搜尋 `eval(`、`exec(`、`shell=True`、`pickle`、`yaml.load`、`verify=False`、裸 `except`、`subprocess`、`password`、`token`，並另查 TLS、`CERT_NONE`、`0.0.0.0` 與閘門開關。排除 `test/`、`tests/`、`build/`、`dist/`、`__pycache__/` 與 `docs/` 產生物。每一則發現都先讀過對應原始碼。未啟動程式、未跑測試、未連線、未寄信。

### 總評

SMTP 與 IMAP 都強制走會驗證憑證與主機名稱的 TLS：隱含 TLS，或先 `STARTTLS` 成功才繼續，失敗就關閉連線並拋出。沒有搜到 `verify=False`、`CERT_NONE` 或明文 `SMTP` / `IMAP4`。JSON 執行器只把 `safe_builtin_commands()` 併進 `event_dict`，`eval`、`exec`、`open`、`__import__` 不是指令；`add_command_to_executor` 與 `project_mail` 也不是動作指令。套件原始碼沒有寫死密碼或權杖。套件閘門的兩個開關只能從 Python 呼叫。

未關閉的缺陷：無。建議 2 則、備註 1 則，都不構成立即損害，也不把設計中的白名單當成缺陷。

### 發現

#### CR-01

- 嚴重度：建議
- 位置：`je_mail_thunder/smtp/smtp_wrapper.py` 的 `later_init`（約第 50–53 行）、`create_message_and_send`（約第 208–222 行）、`create_message_with_attach_and_send`（約第 197–206 行）；`je_mail_thunder/imap/imap_wrapper.py` 的 `later_init`、`select_mailbox`、`search_mailbox`、`mail_content_list`、`output_all_mail_as_file`、`quit`（`except Exception` 後只記錄）
- 說明：這些是 JSON 指令 `MT_smtp_*` / `MT_imap_*` 實際呼叫的舊包裝器。它們抓住 `Exception`、寫入日誌後不重新拋出，函式落到隱含的 `None`。動作紀錄因此分不出「沒有回傳值」和「登入、搜尋或寄送失敗」。同檔 `create_message` 與 `create_message_with_attach` 的 docstring 寫 `:return: None`，實際在成功時回傳訊息物件。新的 `providers/smtp.py` 與 `providers/session.py` 會把失敗轉成 `MailThunderException` 子類再拋出；`session.py` 第 101–104 行的 `except Exception` 是清掉未登入連線後重新拋出，不是同一種問題。
- 依據：審核規範第 3、5 條；`CLAUDE.md` 例外處理（記錄後重新拋出或轉成 `MailThunderException` 子類；不可吞掉）以及「docstring 不可與行為不符」。同檔設計段落要求公開方法記錄失敗，與此並存，所以列建議、不列缺陷。
- 狀態：未關閉
- 建議：舊包裝器的公開動作失敗時應拋出 `MailThunderException` 子類，讓動作紀錄帶著錯誤。docstring 的 `:return:` 改成實際回傳的訊息，或註明失敗時的行為。

#### CR-02

- 嚴重度：建議
- 位置：`je_mail_thunder/imap/imap_wrapper.py` `search_mailbox`（約第 100–109 行，`self.search(charset, search_str)`）；`je_mail_thunder/smtp/smtp_wrapper.py` `create_message_with_attach`（約第 92–94 行，`MIMEMultipart` 後 `message[key] = value`）以及第 64–65、88–90 行的 INFO 日誌
- 說明：JSON 指令 `MT_imap_search_mailbox`、`MT_imap_mail_content_list`、`MT_imap_output_all_mail_as_file` 把搜尋字串直接交給 `imaplib`。`providers/imap.py` 的 `_search_criteria` 已拒絕控制字元，舊路徑沒有。搜尋字串若含換行，有機會在已登入的連線上多送出 IMAP 指令。附件寄送使用 `MIMEMultipart`（標準庫預設 `compat32`，不拒絕標頭值裡的換行）；`create_message` 使用 `EmailMessage`，換行會在標準庫被拒絕，但例外又被 CR-01 的路徑吃掉，所以那條路徑是失敗而不送出。動作檔的作者本來就能指定收件人，也能走 `MT_mail_delete_message`，因此這不是新的遠端能力，列建議。另外，這兩條舊路徑把整段內文與標頭字典寫進 INFO 日誌；`SMTPProvider.send` 只記錄收件人數與附件數。日誌檔會收下整封內容。本次未連線、未寄信，沒有把注入再跑一遍。
- 依據：審核規範第 6 條；`CLAUDE.md` 要求在 JSON 動作與郵件標頭這類邊界驗證輸入，且密碼與權杖不得進入 `mail_thunder_logger`。內文日誌不是寫死憑證，但是與新路徑不一致。
- 狀態：未關閉
- 建議：舊 IMAP 搜尋比照 `_search_criteria`，拒絕控制字元後再查詢。附件訊息改走會拒絕換行的郵件政策，或在寫入標頭前拒絕換行。日誌只留主旨長度或收件人數，不要寫出內文與完整標頭。

#### CR-03

- 嚴重度：備註
- 位置：`je_mail_thunder/utils/package_manager/package_manager_class.py` `PackageManager.__init__`；`je_mail_thunder/utils/executor/action_executor.py` `set_allow_arbitrary_packages`（約第 118–124 行）與 `event_dict` 的 `MT_add_package_to_executor`
- 說明：閘門有接上，拒絕時拋 `ExecuteActionException`。`allow_packages` 與 `set_allow_arbitrary_packages` 不是動作指令，動作檔或 socket 不能自己把閘門打開。宿主尚未呼叫任一開關時，允許清單外的套件仍會載入，並發出 `DeprecationWarning`。這是 `progress.md` #10 已寫明的過渡（要等警告先隨兩個發行版出去，並先決定只有動作檔的使用者如何允許套件），三份 README 與 `docs/source/docs/{Eng,Zh}/package_manager.rst` 寫的是同一件事。`architecture.md` 的 “gate on” 指的是閘門機制在作用，不是預設拒絕。沒有看到繞過 `SAFE_BUILTINS` 的路徑。
- 依據：審核規範第 6、10 條；`progress.md` #10；`action_executor.py` 對該預設的說明。
- 狀態：未關閉（既有追蹤項，非缺陷）
- 建議：維持 #10 的條件再把預設改為拒絕。在那之前，會跑不受信任動作檔的宿主應自行呼叫 `set_allow_arbitrary_packages(False)`。

### 已核對

- TLS：`utils/tls/tls_context.py` 的 `verified_client_context()` 使用 `ssl.create_default_context(ssl.Purpose.SERVER_AUTH)`。`SMTPWrapper` 以這個 context 建立 `SMTP_SSL`；`SMTPStartTLSWrapper` 在建構時呼叫 `starttls`，失敗則 `close()` 後重新拋出；`IMAPWrapper` 只繼承 `IMAP4_SSL` 並傳入同一 context。`SMTPProvider` 只在這兩個包裝器之間選擇。OAuth2 權杖端點與 `providers/http.py` 的 `https_request` 都要求 `https`。
- 憑證：`password` / `token` 的命中是參數、環境變數名稱或 OAuth 流程，不是寫死的秘密。`Authentication.__repr__` 只含使用者；OAuth2 的秘密欄位 `repr=False`。`mail_thunder_content.json` 在 `.gitignore`。預設帳密字典的密碼欄位是空值。
- JSON 白名單：`Executor` 以 `CommandPolicy.FUNCTIONS_ONLY` 建立，`event_dict` 只有 `MT_*` 郵件指令與 `safe_builtin_commands()`。`project_mail` 會執行專案的 `mail/config.py` 與 `triggers.py`，但沒有註冊成動作。
- 其他邊界：socket 預設 `localhost:9942`，先做 `_validate_payload`（最多 256 個動作）。Studio 只綁定 loopback，並檢查每回權杖與 `Host`。Graph webhook 預設 `localhost`，通知要比對 `clientState`。`output_all_mail_as_file` 經 `safe_filename` 與 `commonpath` 擋路徑穿越。
- §6：`project_mail`、`SMTPWrapper`、`read_output_content`、`get_mail_thunder_os_environ`、埠 9942、`start_mail_thunder_socket_server`、`auto_control` 別名與 `SAFE_BUILTINS` 都還在。抽查的熱點函式沒有超過 50 行、7 個參數或行寬 120；未用工具重算複雜度。

### 未涵蓋

未逐行審 `templates/`、`studio/page.py`、`triggers/` 其餘檔與 `scripts/`。未讀 `je_action_core` 套件本體，閘門與 `SAFE_BUILTINS` 的執行細節依本專案的接線、註解與測試檔名稱。未執行 pytest、lint，未對真實信箱或 socket 送資料。`build/` 與文件產出不在範圍內。

### 本專案加嚴

長度採 `CLAUDE.md` 的 50 行函式上限，而不是審核共通的 80 行。安全上除了共通的不寫死憑證、不關 TLS，還核對了：JSON 不得註冊白名單外的內建函式、`project_mail` 不得成為動作、每個 SMTP/IMAP 連線都要帶驗證用的 context、套件閘門的開關不得出現在 `event_dict`。

### 結論

通過。未關閉缺陷 0。建議 2（CR-01 舊包裝器吞掉 SMTP/IMAP 失敗；CR-02 舊路徑的 IMAP 搜尋字串、附件標頭換行與整封內容日誌）。備註 1（CR-03 套件閘門預設仍會在警告後載入清單外套件，屬 progress.md #10，不是白名單被繞過）。沒有發現 TLS 被關掉，也沒有發現寫死的憑證。
