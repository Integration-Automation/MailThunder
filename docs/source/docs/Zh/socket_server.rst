Socket 伺服器
==============

MailThunder 內建 TCP Socket 伺服器，接收遠端 JSON 動作命令，
實現透過網路遠端控制郵件自動化工作流程。

伺服器建構於 Python 的 ``socketserver.ThreadingMixIn`` 和 ``socketserver.TCPServer``，
以獨立執行緒處理每個客戶端連線。

----

啟動伺服器
----------

.. code-block:: python

   from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import (
       start_autocontrol_socket_server
   )

   server = start_autocontrol_socket_server(host="localhost", port=9944)
   # 伺服器正在背景 daemon 執行緒中運行

**參數：**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - 參數
     - 預設值
     - 說明
   * - ``host``
     - ``"localhost"``
     - 綁定的主機地址
   * - ``port``
     - ``9944``
     - 監聽的 TCP 埠號

伺服器執行緒為 daemon 執行緒 — 當主程式結束時會自動終止。

----

傳送命令至伺服器
----------------

命令以 JSON 編碼的動作列表傳送（與 ``auto_control`` 列表格式相同，
不含包裝鍵）：

.. code-block:: python

   import socket
   import json

   # 連接伺服器
   client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client.connect(("localhost", 9944))

   # 傳送動作命令列表
   command = json.dumps([
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
           "message_content": "透過 socket 伺服器寄送！",
           "message_setting_dict": {
               "Subject": "遠端郵件",
               "To": "receiver@gmail.com",
               "From": "sender@gmail.com"
           }
       }],
       ["smtp_quit"]
   ])
   client.send(command.encode("utf-8"))

   # 接收回應
   response = client.recv(8192).decode("utf-8")
   print(response)

   client.close()

----

伺服器協定
----------

**請求格式：**

.. code-block:: text

   客戶端 ──▶ 伺服器: JSON 編碼的動作列表（UTF-8 位元組，最大 8192 位元組）

**回應格式：**

.. code-block:: text

   伺服器 ──▶ 客戶端: 對每個命令結果:
                          <回傳值>\n
                      接著終止符:
                          Return_Data_Over_JE\n

**關閉：**

.. code-block:: text

   客戶端 ──▶ 伺服器: "quit_server"（純文字字串，非 JSON）
   伺服器: 優雅關閉

----

完整範例：客戶端-伺服器互動
----------------------------

**伺服器端 (server.py)：**

.. code-block:: python

   from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import (
       start_autocontrol_socket_server
   )
   import time

   server = start_autocontrol_socket_server("localhost", 9944)
   print("伺服器已在 localhost:9944 啟動")

   try:
       while not server.close_flag:
           time.sleep(1)
   except KeyboardInterrupt:
       server.shutdown()
       print("伺服器已停止")

**客戶端 (client.py)：**

.. code-block:: python

   import socket
   import json

   def send_command(host, port, actions):
       client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       client.connect((host, port))
       client.send(json.dumps(actions).encode("utf-8"))
       response = client.recv(8192).decode("utf-8")
       client.close()
       return response

   # 遠端寄送郵件
   result = send_command("localhost", 9944, [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
           "message_content": "遠端郵件！",
           "message_setting_dict": {
               "Subject": "Socket 伺服器測試",
               "To": "receiver@gmail.com",
               "From": "sender@gmail.com"
           }
       }],
       ["smtp_quit"]
   ])
   print("結果:", result)

   # 關閉伺服器
   result = send_command("localhost", 9944, "quit_server")

.. note::

   ``quit_server`` 命令是純文字字串，**不是** JSON 編碼的動作列表。

----

伺服器架構
----------

.. code-block:: text

   TCPServer (socketserver.ThreadingMixIn + socketserver.TCPServer)
       │
       ├── server.serve_forever()    ← 在 daemon 執行緒中運行
       │
       └── 對每個客戶端連線:
               │
               ▼
           TCPServerHandler.handle()
               │
               ├── recv(8192) ← 讀取命令位元組
               │
               ├── command == "quit_server"
               │       └── server.shutdown()
               │
               └── command 是 JSON 動作列表
                       │
                       ▼
                   execute_action(json.loads(command))
                       │
                       ▼
                   sendto(result) 對每個動作結果
                   sendto("Return_Data_Over_JE")

**重要屬性：**

- ``server.close_flag`` — ``bool``，收到 ``quit_server`` 時設為 ``True``
- 每個連線在新執行緒中處理（``ThreadingMixIn``）
- 最大接收緩衝：每個命令 8192 位元組
- 編碼：UTF-8

----

安全性考量
----------

.. warning::

   Socket 伺服器 **不提供** 任何認證或加密。
   任何可連接到 host:port 的客戶端都可以執行命令。

   **請勿** 在沒有額外安全措施的情況下將 Socket 伺服器暴露到公共網路
   （防火牆規則、SSH 隧道、TLS 包裝等）。

   預設綁定到 ``localhost`` 僅限本機存取。
