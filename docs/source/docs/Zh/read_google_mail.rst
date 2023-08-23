讀取 Google 郵件使用 IMAP
----

.. code-block:: python

    from je_mail_thunder import IMAPWrapper

    # 設定 IMAP host
    imap_host = 'imap.gmail.com'
    # 初始化 IMAPWrapper
    imap_wrapper = IMAPWrapper(host=imap_host)
    imap_wrapper.imap_later_init()
    # 選擇郵件箱
    imap_wrapper.select()
    # 取得郵件 list
    mail_list = imap_wrapper.imap_mail_content_list()
    # 輸出郵件 主旨 從哪個郵件地址寄送到哪個地址 郵件 BODY
    for mail in mail_list:
        print(mail.get("SUBJECT"))
        print(mail.get("FROM"))
        print(mail.get("TO"))
        print(mail.get("BODY"))
    # 退出
    imap_wrapper.imap_quit()
