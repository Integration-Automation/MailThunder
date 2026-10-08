郵件模板
========

郵件模板包含主旨、純文字內文與 HTML 內文，三者共用同一份 context，
所以報表郵件只要寫一次，就能帶入不同的數字寄出。

.. code-block:: python

   from je_mail_thunder import Mail

   with Mail() as mail:
       mail.send(
           to="qa@example.com",
           template="test_report",
           context={"project": "APITestka", "passed": 98, "failed": 2,
                    "failures": [{"name": "login", "seconds": 1.5}]},
       )

模板負責產生主旨與內文；其他欄位（``to``、``attachments`` 等）照常提供。
與 ``template=`` 同時給的欄位優先於模板產生的結果，所以 ``subject="..."`` 可以只替這一封信換掉主旨。

----

模板放在哪裡
------------

``Mail`` 以名稱尋找模板：先找專案的 ``mail/templates/`` 目錄（位於工作目錄之下），
再找共用目錄：``~/.je_mail_thunder/templates``，或 ``MAIL_THUNDER_TEMPLATE_DIR`` 指定的目錄。

模板可以是一個目錄：

.. code-block:: text

   mail/templates/test_report/
     subject.txt      # [{{ project }}] {{ passed }} passed, {{ failed }} failed
     body.txt         # 純文字內文
     body.html        # HTML 內文
     template.json    # 選用：變數與 metadata

也可以是一個 JSON 檔 ``mail/templates/test_report.json``：

.. code-block:: json

   {
     "subject": "[{{ project }}] {{ passed }} passed, {{ failed }} failed",
     "text": "Project {{ project }} finished.",
     "html": "<h1>{{ project }}</h1>",
     "variables": {
       "project": {"description": "專案名稱"},
       "passed": {},
       "failed": {"default": 0}
     },
     "metadata": {"owner": "qa"}
   }

模板至少要有三個部分中的一個。名稱只能包含字母、數字、``_``、``-`` 與 ``.``，不能是路徑。
要從別的地方載入時，給 ``Mail`` 自己的 loader：

.. code-block:: python

   from je_mail_thunder import Mail, MailTemplate, TemplateLoader

   mail = Mail(templates=TemplateLoader(["reports/templates", "/srv/shared/templates"]))
   mail.templates.add(MailTemplate("welcome", subject="Hi {{ name }}", text="Welcome, {{ name }}."))
   print(mail.templates.names())

----

模板語法
--------

語法是 Jinja2 中郵件用得到的部分，以標準函式庫實作。

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - 語法
     - 意義
   * - ``{{ user.name }}``
     - 一個值。以點號取得 dict、list（``items.0``）與公開屬性的內容
   * - ``{{ name | upper }}``
     - 過濾器；可以連續使用多個
   * - ``{% if failed > 0 %} ... {% elif skipped %} ... {% else %} ... {% endif %}``
     - 條件：一個值、``not`` 一個值，或與另一個值、文字、數字、``true``、``false``、``none``
       做一次比較（``== != < <= > >=``）
   * - ``{% for test in failures %} ... {% endfor %}``
     - 迴圈。迴圈內可用 ``loop.index``\ （從 1 開始）、``loop.first``、``loop.last`` 與 ``loop.length``
   * - ``{# note #}``
     - 註解

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - 過濾器
     - 結果
   * - ``upper``、``lower``、``title``、``trim``
     - 轉換大小寫，或去除前後空白
   * - ``length``
     - 項目數量
   * - ``join(", ")``
     - 把 list 的項目接成一段文字（沒有給分隔符號時為 ``", "``）
   * - ``default("none")``
     - context 沒有這個名稱時使用指定的值
   * - ``safe``
     - 在 HTML 內文中：不做跳脫，直接輸出該值

值得知道的規則：

- 獨占一行的 ``{% ... %}`` 標籤會連同該行一起消失，所以區塊標籤不會留下空白行。
- HTML 內文中的每個值都會做 HTML 跳脫，除非經過 ``safe``。主旨與純文字內文不會跳脫。
- context 沒有的名稱在輸出時是錯誤，在條件中則視為 false。
- 模板只能讀取 context。它不能呼叫任何東西、不能取得以 ``_`` 開頭的名稱，也不會執行 Python。

----

變數與錯誤
----------

``variables`` 宣告 context 必須包含什麼：可以是名稱的清單，或是把每個名稱對應到
``{"description": ..., "default": ...}`` 的 mapping。有 ``default`` 的變數是選用的。
宣告過的變數會在開始產生內容之前檢查，缺少的變數會一次全部回報。

.. code-block:: python

   from je_mail_thunder import Mail
   from je_mail_thunder.utils.exception.exceptions import TemplateContextError

   mail = Mail()
   try:
       mail.send(to="qa@example.com", template="test_report", context={"passed": 98})
   except TemplateContextError as error:
       print(error.template, error.missing)      # test_report ('project',)

   preview = mail.render("test_report", {"project": "APITestka", "passed": 98})
   print(preview.subject, preview.text, preview.html)

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - 例外
     - 引發時機
   * - ``TemplateNotFound``
     - 沒有任何目錄包含該模板（``name``、``searched``）
   * - ``TemplateSyntaxError``
     - 某個部分不是有效的模板語法（``line``）
   * - ``TemplateContextError``
     - context 缺少模板需要的變數（``missing``、``template``）
   * - ``TemplateRenderError``
     - 某個值不適用於模板對它做的事，或輸出超過 5 MiB

它們都繼承自 ``MailThunderTemplateException``。模板失敗時不會寄出任何東西。

產生出來的主旨仍然必須是單行：context 的值若讓主旨帶有換行，
會被每封寄出郵件都要通過的檢查拒絕（:doc:`mail_api`）。

----

在動作檔中使用
--------------

.. code-block:: json

   {
     "mail_thunder": [
       ["MT_mail_render_template", {"template": "test_report", "context": {"project": "APITestka", "passed": 98}}],
       ["MT_mail_send", {"to": "qa@example.com", "template": "test_report",
                         "context": {"project": "APITestka", "passed": 98}}]
     ]
   }

``MT_mail_render_template`` 回傳 ``{"subject": ..., "text": ..., "html": ...}``，不會寄出任何東西。
