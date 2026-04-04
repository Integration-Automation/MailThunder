安裝指南
========

本頁說明所有安裝 MailThunder 的方式。

系統需求
--------

- **Python 3.9** 以上
- 無需額外相依套件 (僅使用 Python 標準函式庫)
- ``pip`` 套件管理工具

從 PyPI 安裝
-------------

**穩定版本：**

.. code-block:: bash

   pip install je_mail_thunder

**開發版本** (最新功能，可能不穩定)：

.. code-block:: bash

   pip install je_mail_thunder_dev

從原始碼安裝
------------

克隆儲存庫並以可編輯（開發）模式安裝：

.. code-block:: bash

   git clone https://github.com/Integration-Automation/MailThunder.git
   cd MailThunder
   pip install -e .

安裝開發相依套件
-----------------

若您計劃貢獻程式碼或執行測試套件：

.. code-block:: bash

   pip install -r dev_requirements.txt

包含：

- ``pytest`` — 用於執行單元測試
- ``coverage`` — 用於程式碼覆蓋率報告

驗證安裝
--------

安裝完成後，驗證 MailThunder 是否可用：

.. code-block:: bash

   python -c "import je_mail_thunder; print('MailThunder 安裝成功')"

查看版本資訊：

.. code-block:: bash

   pip show je_mail_thunder

升級
----

升級至最新版本：

.. code-block:: bash

   pip install --upgrade je_mail_thunder

解除安裝
--------

.. code-block:: bash

   pip uninstall je_mail_thunder
