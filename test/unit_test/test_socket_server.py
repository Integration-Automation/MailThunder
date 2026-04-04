import json
import socket
import time
import threading

from je_mail_thunder.utils.socket_server.mail_thunder_socket_server import (
    start_autocontrol_socket_server,
)
from je_mail_thunder.utils.executor.action_executor import add_command_to_executor


def _send_and_recv(host, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode("utf-8"))
        chunks = []
        while True:
            data = s.recv(4096)
            if not data:
                break
            chunks.append(data.decode("utf-8"))
        return "".join(chunks)


def test_socket_server_execute_command():
    server = start_autocontrol_socket_server("127.0.0.1", 0)
    port = server.server_address[1]
    try:
        command = json.dumps([["print", ["socket_test"]]])
        response = _send_and_recv("127.0.0.1", port, command)
        assert "Return_Data_Over_JE" in response
    finally:
        server.shutdown()


def test_socket_server_quit():
    server = start_autocontrol_socket_server("127.0.0.1", 0)
    port = server.server_address[1]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", port))
            s.sendall(b"quit_server")
        for _ in range(20):
            if server.close_flag:
                break
            time.sleep(0.1)
        assert server.close_flag is True
    finally:
        try:
            server.shutdown()
        except Exception:
            pass
