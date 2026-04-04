MailThunder 繁體中文文件
========================

歡迎來到 MailThunder 繁體中文文件。本節涵蓋如何使用 MailThunder 寄送與讀取郵件、
認證設定、腳本引擎等功能。

.. toctree::
    :maxdepth: 4
    :caption: 中文指南

    send_google_mail.rst
    read_google_mail.rst

----

前置需求
--------

使用 MailThunder 之前，請確認:

1. 已安裝 **Python 3.9+**
2. 已透過 ``pip install je_mail_thunder`` 安裝 **MailThunder**
3. 已設定好 **郵件認證資訊** (請參考下方認證設定)

認證設定
--------

MailThunder 支援兩種認證方式。系統會先嘗試 JSON 設定檔，若找不到則使用環境變數。

**方式一：JSON 設定檔**

在目前工作目錄下建立 ``mail_thunder_content.json``：

.. code-block:: json

    {
        "user": "your_email@gmail.com",
        "password": "your_app_password"
    }

**方式二：環境變數**

.. code-block:: python

    from je_mail_thunder import set_mail_thunder_os_environ

    set_mail_thunder_os_environ(
        mail_thunder_user="your_email@gmail.com",
        mail_thunder_user_password="your_app_password"
    )

或者在終端機設定：

.. code-block:: bash

    export mail_thunder_user="your_email@gmail.com"
    export mail_thunder_user_password="your_app_password"

.. note::

    **Gmail 使用者注意：** 您必須使用
    `應用程式密碼 <https://support.google.com/accounts/answer/185833>`_，
    而非一般的 Google 帳戶密碼。同時需要在 Gmail 設定中
    `啟用 IMAP <https://support.google.com/mail/answer/7126229>`_。

----
