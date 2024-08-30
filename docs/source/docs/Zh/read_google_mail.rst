使用 IMAP 讀取 Google 郵件
----

.. code-block:: python

    from je_mail_thunder import IMAPWrapper, set_mail_thunder_os_environ

    # 設置 IMAP 主機
    imap_host = 'imap.gmail.com'
    # 初始 IMAP 包裝類別
    imap_wrapper = IMAPWrapper(host=imap_host)

    set_mail_thunder_os_environ(
        "test_user", # your user
        "test_password" # your password
    )

    imap_wrapper.later_init()
    # 選擇搜尋的信箱 (沒有帶參數是全部)
    imap_wrapper.select()
    # 取得郵件列表
    mail_list = imap_wrapper.mail_content_list()
    # 輸出基本資訊
    for mail in mail_list:
        print(mail.get("SUBJECT"))
        print(mail.get("FROM"))
        print(mail.get("TO"))
        print(mail.get("BODY"))
    # 離開
    imap_wrapper.quit()
