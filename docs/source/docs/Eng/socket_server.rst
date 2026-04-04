Socket Server
=============

MailThunder includes a TCP socket server that accepts JSON action commands remotely,
enabling remote control of email automation workflows over the network.

The server is built on Python's ``socketserver.ThreadingMixIn`` and
``socketserver.TCPServer``, handling each client connection in a separate thread.

----

Starting the Server
-------------------

.. code-block:: python

   from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import (
       start_autocontrol_socket_server
   )

   server = start_autocontrol_socket_server(host="localhost", port=9944)
   # Server is now running in a daemon background thread

**Parameters:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Parameter
     - Default
     - Description
   * - ``host``
     - ``"localhost"``
     - Host address to bind to
   * - ``port``
     - ``9944``
     - TCP port to listen on

The server can also accept ``host`` and ``port`` from ``sys.argv``:

- ``sys.argv[1]`` → ``host``
- ``sys.argv[2]`` → ``port``

The server thread is a daemon thread — it will be automatically terminated when
the main program exits.

----

Sending Commands to the Server
------------------------------

Commands are sent as JSON-encoded action lists (the same format as the
``auto_control`` list without the wrapper key):

.. code-block:: python

   import socket
   import json

   # Connect to the server
   client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client.connect(("localhost", 9944))

   # Send an action command list
   command = json.dumps([
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
           "message_content": "Sent via socket server!",
           "message_setting_dict": {
               "Subject": "Remote Email",
               "To": "receiver@gmail.com",
               "From": "sender@gmail.com"
           }
       }],
       ["smtp_quit"]
   ])
   client.send(command.encode("utf-8"))

   # Receive response
   response = client.recv(8192).decode("utf-8")
   print(response)

   client.close()

----

Server Protocol
---------------

**Request format:**

.. code-block:: text

   Client ──▶ Server: JSON-encoded action list (UTF-8 bytes, max 8192 bytes)

**Response format:**

.. code-block:: text

   Server ──▶ Client: For each command result:
                          <return_value>\n
                      Followed by terminator:
                          Return_Data_Over_JE\n

**Shutdown:**

.. code-block:: text

   Client ──▶ Server: "quit_server"  (literal string, not JSON)
   Server: Shuts down gracefully

----

Example: Full Client-Server Interaction
---------------------------------------

**Server (server.py):**

.. code-block:: python

   from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import (
       start_autocontrol_socket_server
   )
   import time

   server = start_autocontrol_socket_server("localhost", 9944)
   print("Server started on localhost:9944")

   # Keep the main thread alive
   try:
       while not server.close_flag:
           time.sleep(1)
   except KeyboardInterrupt:
       server.shutdown()
       print("Server stopped")

**Client (client.py):**

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

   # Send an email remotely
   result = send_command("localhost", 9944, [
       ["MT_smtp_later_init"],
       ["MT_smtp_create_message_and_send", {
           "message_content": "Remote email!",
           "message_setting_dict": {
               "Subject": "Socket Server Test",
               "To": "receiver@gmail.com",
               "From": "sender@gmail.com"
           }
       }],
       ["smtp_quit"]
   ])
   print("Result:", result)

   # Shut down the server
   result = send_command("localhost", 9944, "quit_server")

.. note::

   The ``quit_server`` command is a literal string, **not** a JSON-encoded action list.

----

Server Architecture
-------------------

.. code-block:: text

   TCPServer (socketserver.ThreadingMixIn + socketserver.TCPServer)
       │
       ├── server.serve_forever()    ← runs in daemon thread
       │
       └── For each client connection:
               │
               ▼
           TCPServerHandler.handle()
               │
               ├── recv(8192) ← read command bytes
               │
               ├── command == "quit_server"
               │       └── server.shutdown()
               │
               └── command is JSON action list
                       │
                       ▼
                   execute_action(json.loads(command))
                       │
                       ▼
                   sendto(result) for each action result
                   sendto("Return_Data_Over_JE")

**Key properties:**

- ``server.close_flag`` — ``bool``, set to ``True`` when ``quit_server`` is received
- Each connection is handled in a new thread (``ThreadingMixIn``)
- Max receive buffer: 8192 bytes per command
- Encoding: UTF-8

----

Security Considerations
-----------------------

.. warning::

   The socket server does **not** provide any authentication or encryption.
   Any client that can connect to the host:port can execute commands.

   **Do not** expose the socket server to public networks without additional
   security measures (firewall rules, SSH tunneling, TLS wrapper, etc.).

   By default, binding to ``localhost`` restricts access to the local machine only.
