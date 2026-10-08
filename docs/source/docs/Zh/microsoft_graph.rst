Microsoft Graph
===============

``microsoft_graph`` 供應商透過 Microsoft Graph API 存取 Microsoft 365 信箱，而不是 SMTP 與 IMAP。
``Mail`` 的呼叫方式完全相同，只有供應商名稱不同。

.. code-block:: python

   from je_mail_thunder import Mail, OAuth2Auth, OAuth2Settings

   auth = OAuth2Auth(OAuth2Settings(
       user="you@contoso.com", provider="microsoft", tenant="contoso.onmicrosoft.com",
       client_id="...", client_secret="...", refresh_token="...",
   ))
   with Mail(provider="microsoft_graph", auth=auth) as mail:
       mail.send(to="qa@example.com", subject="Report", html="<b>42 passed</b>", attachments=["report.pdf"])
       for message in mail.get_messages(limit=10, unread_only=True):
           print(message.sender, message.subject)

----

如何選用
--------

- 在程式中：``Mail(provider="microsoft_graph")`` 或 ``MailAccount(provider="microsoft_graph")``。
- 對 ``Mail()`` 與 ``MT_mail_*`` 命令：在 ``mail_thunder_content.json`` 加上
  ``"mail_provider": "microsoft_graph"``，或設定環境變數 ``mail_thunder_mail_provider``。

.. code-block:: json

   {
     "user": "you@contoso.com",
     "mail_provider": "microsoft_graph",
     "oauth2": {
       "provider": "microsoft",
       "tenant": "contoso.onmicrosoft.com",
       "client_id": "...",
       "client_secret": "...",
       "refresh_token": "..."
     }
   }

``microsoft`` 仍然代表透過 SMTP 與 IMAP 存取 Microsoft 365。``mail_provider`` 可以是任何已註冊的供應商，
所以也能選擇 ``smtp`` 或你自己的供應商。

----

登入
----

Graph 需要 OAuth2：密碼無法取得授權。Microsoft Entra 的應用程式註冊需要委派權限 ``Mail.Send`` 與
``Mail.ReadWrite``\ （以及取得 refresh token 所需的 ``offline_access``）。

OAuth2 設定就是 :doc:`authentication` 說明的那一組。設定沒有指定 ``scope`` 時，供應商會以 Graph 的 scope
（``https://graph.microsoft.com/Mail.Send``、``https://graph.microsoft.com/Mail.ReadWrite``、``offline_access``）
取得權杖；設定中若有 ``scope`` 或 ``access_token`` 則照原樣使用。
refresh token 必須來自包含 Graph 權限的同意流程。

----

功能
----

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 呼叫
     - 透過 Graph
   * - ``send``
     - 附件不大時是一次 ``POST /me/sendMail``。否則先建立草稿，把每個附件加上去
       （超過 3 MiB 的走 upload session），再把草稿寄出
   * - ``create_draft``
     - ``POST /me/messages``，或建立在指定的資料夾。回傳草稿的識別碼
   * - ``get_messages``
     - ``GET /me/mailFolders/{folder}/messages``，最新的在前，一次一頁 25 封。``query`` 是 OData 的
       ``$filter`` 運算式，例如 ``from/emailAddress/address eq 'ci@example.com'``
   * - ``get_message`` / ``delete_message``
     - ``GET`` / ``DELETE /me/messages/{id}``；``message_id`` 是 Graph 的識別碼

資料夾可以用 ``INBOX``、``Drafts``、``Sent``、``Deleted Items``、``Junk``、``Archive``，或顯示名稱來指定。
與 SMTP 的差異：

- 郵件只有一個內文：同時給 ``text`` 與 ``html`` 時，Graph 收到的是 HTML；
- 自訂標頭必須以 ``X-`` 開頭；
- ``sender`` 若不是帳號本人，需要 Microsoft 365 的「以…身分傳送」權限。

錯誤與其他 API 一致：權杖被拒絕（HTTP 401 或 403）是 ``MailThunderAuthenticationException``，
連不上 Graph 是 ``MailThunderConnectionException``，郵件被拒絕是 ``MailThunderSendException``，
其他則是帶有 Graph 錯誤代碼與訊息的 ``MailThunderProviderException``。
請求只會送往 ``https://graph.microsoft.com``。

----

觸發器
------

對 Graph 帳號呼叫 ``mail.watch()`` 會使用 ``GraphPollingBackend``，它在第一次查看之後只詢問之後收到的郵件。

``GraphWebhookBackend`` 則是讓 Graph 主動通知新郵件（change notifications）。Graph 會對一個公開的 HTTPS
位址送出 POST，所以後端的監聽器（綁定 ``localhost:9946``）必須放在反向代理或通道之後：

.. code-block:: python

   from je_mail_thunder import GraphWebhookBackend, Mail

   mail = Mail(provider="microsoft_graph")
   mail.on("message_received", lambda event: print(event.message.subject))
   provider = mail.providers[0]
   backend = mail.triggers.add(GraphWebhookBackend(provider, "https://hooks.example.com/mail"))
   backend.start()      # 開啟監聽器、建立訂閱，並在執行期間持續更新訂閱
   ...
   mail.close()         # 移除訂閱並關閉監聽器

後端會回應 Graph 的驗證請求，並忽略沒有帶著隨機密鑰（``clientState``）與自己訂閱識別碼的通知，
因為任何人都能對公開位址送出 POST。通知只會指出是哪一封郵件；後端接著再透過 Graph 讀取它。
