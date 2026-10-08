附件政策
========

``AttachmentPolicy`` 定義一封郵件可以攜帶什麼：附件的數量、大小與類型。
``validate_attachments`` 會在寄出任何東西之前，依政策檢查郵件的附件，
並在第一條被違反的規則處引發結構化例外。

----

定義政策
--------

.. code-block:: python

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

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - 設定
     - 預設值
     - 意義
   * - ``max_file_size``
     - ``None``
     - 單一附件可以有的位元組數
   * - ``max_total_size``
     - ``None``
     - 一封郵件所有附件合計可以有的位元組數
   * - ``max_count``
     - ``None``
     - 一封郵件可以攜帶的附件數量
   * - ``allowed_extensions``
     - ``None``
     - 唯一接受的副檔名。``"pdf"`` 與 ``".PDF"`` 視為相同；以最後一個副檔名為準，
       所以 ``report.pdf.exe`` 是 ``.exe``
   * - ``allowed_mime_types``
     - ``None``
     - 唯一接受的 MIME 類型。``"image/*"`` 接受所有圖片類型

``None`` 表示不設限，因此 ``AttachmentPolicy()`` 允許所有存在的檔案。上限若為負數或非整數，
或類型集合不是字串的集合，建立政策時就會引發 ``MailThunderAttachmentException``。

``DEFAULT_ATTACHMENT_POLICY`` 允許單一附件與整封郵件各 25 MiB、任何類型：
這是 Gmail 與 Microsoft 365 接受的郵件大小。

.. note::

   類型檢查看的是檔名，不是檔案內容。它能防止誤寄錯誤的檔案，無法防止刻意改名的檔案。

----

驗證流程
--------

檢查依下列順序進行，第一個失敗的檢查就會引發例外：

.. code-block:: text

   數量 -> 是否存在 -> 大小 -> 副檔名 -> MIME 類型 -> 合計大小

.. list-table::
   :header-rows: 1
   :widths: 32 38 30

   * - 例外
     - 引發時機
     - 屬性
   * - ``AttachmentCountExceeded``
     - 附件數量超過 ``max_count``
     - ``count``、``limit``
   * - ``AttachmentNotFound``
     - 要附加的檔案不存在，或不是一般檔案
     - ``path``
   * - ``AttachmentTooLarge``
     - 單一附件超過 ``max_file_size``
     - ``filename``、``size``、``limit``
   * - ``AttachmentTypeNotAllowed``
     - 副檔名或 MIME 類型不在允許範圍內
     - ``filename``、``kind``\ （``"extension"`` 或 ``"MIME type"``）、``value``
   * - ``TotalAttachmentSizeExceeded``
     - 附件合計超過 ``max_total_size``
     - ``size``、``limit``

它們都繼承自 ``MailThunderAttachmentException``：

.. code-block:: python

   from je_mail_thunder.utils.exception.exceptions import (
       AttachmentTooLarge,
       MailThunderAttachmentException,
   )

   try:
       validate_attachments(attachments, policy)
   except AttachmentTooLarge as error:
       print(f"{error.filename} 有 {error.size} 位元組；上限是 {error.limit}")
   except MailThunderAttachmentException as error:
       print(f"附件被拒絕：{error}")

每次失敗在引發之前，也會透過 ``mail_thunder_logger`` 記錄。

----

附件
----

``Attachment`` 是要寄送的檔案，或是隨郵件收到的檔案。

.. code-block:: python

   from je_mail_thunder import Attachment

   # 要寄送的檔案。建立郵件時才會開啟。
   report = Attachment.from_path("out/report-2026-10.pdf", filename="report.pdf")
   print(report.filename, report.content_type, report.size)

   # 收到的附件：位元組內容在 ``content``。
   received = Attachment(filename="notes.txt", content_type="text/plain", content=b"...")
   path = received.save("downloads")

``Attachment.from_path`` 可指定收件者看到的檔名（預設為檔案本身的名稱）與 MIME 類型
（預設由檔名推測；檔名看不出類型時為 ``application/octet-stream``）。

安全地儲存收到的附件
~~~~~~~~~~~~~~~~~~~~

收到的附件檔名是寄件者寫的任意內容。``Attachment.save(directory)`` 會先把檔名處理成安全的名稱再寫入，
因此檔案不會落在 ``directory`` 之外：

- 去除兩種分隔符號的目錄部分（``../../etc/passwd`` 變成 ``passwd``）；
- ``..``、控制字元與 Windows 不接受的字元（``: * ? " < > |``）會被取代；
- Windows 裝置名稱（``NUL``、``COM1``）會加上底線前綴；
- 處理後什麼都不剩的檔名變成 ``attachment``。

同一個函式也可從 ``je_mail_thunder.attachments.mime.safe_filename`` 取得。

.. note::

   ``SMTPWrapper`` 的方法（``create_message_with_attach_and_send``）不會套用政策。
   使用它們之前，請自行呼叫 ``validate_attachments``。
