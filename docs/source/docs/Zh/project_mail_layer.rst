專案郵件層
==========

自動化專案把「怎麼寄信」放在自己的 ``mail/`` 目錄裡，程式只要取得一個設定好的 ``Mail``，不必指定供應商。
之後要把專案換到另一家供應商，或是不寄出任何東西先試跑，都只需要修改一個檔案。

.. code-block:: text

   MyProject/
     api/
     reports/
     mail/
       config.py       # 供應商、登入方式、附件政策、稽核日誌
       triggers.py     # 郵件到達或失敗時專案要做的事
       templates/      # 專案自己的郵件模板
         test_report/
           subject.txt
           body.txt
           body.html
           template.json

.. code-block:: python

   from je_mail_thunder import project_mail

   mail = project_mail()                    # 工作目錄中的專案
   mail.send(to="qa@example.com", template="test_report",
             context={"project": "MyProject", "passed": 98, "failed": 2,
                      "failures": [{"name": "login", "reason": "timeout"}]})
   mail.triggers.poll()                     # 查看一次有沒有新郵件
   mail.close()

``create_project_dir()`` 會連同 ``keyword/`` 與 ``executor/`` 目錄一起建立這一層（:doc:`project_templates`）。
建立出來的 ``config.py`` 使用 ``file`` 供應商，所以新專案在指定真正的供應商之前，郵件都只會留在磁碟上。

----

config.py
---------

每個名稱都是選用的。沒有 ``config.py`` 時，專案得到的 ``Mail()`` 與其他程式相同。

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 名稱
     - 意義
   * - ``PROVIDER``
     - 已註冊的供應商名稱：``"google"``、``"microsoft"``、``"microsoft_graph"``、``"yahoo"``、
       ``"icloud"``、``"zoho"``、``"fastmail"``、``"smtp"`` 或 ``"file"``
   * - ``AUTH``
     - 認證物件。省略時登入資訊來自 ``mail_thunder_content.json`` 或環境變數，
       這樣認證資訊就不會出現在專案的檔案裡
   * - ``ACCOUNT``
     - 完整的 ``MailAccount``\ （``"smtp"`` 需搭配 ``MailServers``），用來取代 ``PROVIDER`` 與 ``AUTH``
   * - ``ATTACHMENT_POLICY``
     - 專案每封郵件都要通過的 ``AttachmentPolicy``
   * - ``AUDIT``
     - ``True`` 會把每個郵件事件記錄到 ``mail/audit.jsonl``；給路徑則記錄到該檔案；``False`` 不記錄

.. code-block:: python

   from je_mail_thunder import AttachmentPolicy

   PROVIDER = "microsoft_graph"
   ATTACHMENT_POLICY = AttachmentPolicy(max_total_size=20 * 1024 * 1024, allowed_extensions={"html", "pdf"})
   AUDIT = True

.. warning::

   如果專案會提交到版本庫，請不要把密碼或權杖寫在 ``config.py``。
   省略 ``AUTH``，讓登入資訊來自 ``mail_thunder_content.json``\ （已被 git 忽略）或環境變數。

----

triggers.py
-----------

``triggers.py`` 定義 ``register(mail)``，``project_mail`` 會呼叫它一次。它負責訂閱專案的處理函式，
並指定要監看哪些資料夾（:doc:`mail_triggers`）。

.. code-block:: python

   def register(mail):
       @mail.on("message_received", filter={"subject": "[RERUN]"})
       def rerun_requested(event):
           print("rerun requested by", event.message.sender)

       @mail.on("message_failed")
       def report_not_sent(event):
           print("report not sent:", event.error)

       mail.watch("INBOX", start=False)     # start=True 會在背景執行緒監看

----

templates/
----------

專案的模板會比共用模板先被找到，所以專案可以用同名模板取代共用模板（:doc:`mail_templates`）。

----

載入了什麼、何時載入
--------------------

- ``project_mail(project=None)`` 會執行 ``mail/config.py`` 與 ``mail/triggers.py``。它們是專案的 Python 檔，
  執行方式與專案的其他模組相同：只載入你信任其程式碼的專案。沒有任何動作命令會載入這一層，
  所以動作檔或 Socket 客戶端無法讓它被執行。
- ``describe_mail_layer(project=None)`` 只查看檔案：哪些檔案存在、有哪些模板。它不會執行任何東西。
- 在使用 ``Mail`` 之前不會連線；除非 ``triggers.py`` 啟動觸發器，否則也不會有觸發器在執行。
- 專案沒有 ``mail`` 目錄、設定的型別錯誤、檔案無法執行，或 ``triggers.py`` 沒有 ``register`` 時，
  會引發指出該檔案的 ``MailThunderProjectException``。
