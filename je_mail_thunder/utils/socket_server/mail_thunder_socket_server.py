import json
import socketserver
import sys
import threading

from je_mail_thunder.utils.executor.action_executor import execute_action

MAX_PAYLOAD_BYTES = 8192
MAX_ACTIONS = 256


def _validate_payload(payload):
    """
    Validate the decoded JSON payload structure before execution.
    Accepts either a list of action entries or a dict with an
    "auto_control" key mapping to such a list. Each action entry must
    be a non-empty list whose first element is a string command name.
    """
    if isinstance(payload, dict):
        actions = payload.get("auto_control")
        if not isinstance(actions, list):
            raise ValueError("payload dict must contain 'auto_control' list")
    elif isinstance(payload, list):
        actions = payload
    else:
        raise ValueError("payload must be a dict or list")
    if len(actions) == 0:
        raise ValueError("action list is empty")
    if len(actions) > MAX_ACTIONS:
        raise ValueError(f"action list exceeds max length {MAX_ACTIONS}")
    for entry in actions:
        if not isinstance(entry, list) or len(entry) == 0 or len(entry) > 2:
            raise ValueError(f"invalid action entry: {entry!r}")
        if not isinstance(entry[0], str):
            raise ValueError(f"action command name must be str: {entry!r}")


class TCPServerHandler(socketserver.BaseRequestHandler):

    def handle(self):
        raw = self.request.recv(MAX_PAYLOAD_BYTES).strip()
        if len(raw) >= MAX_PAYLOAD_BYTES:
            print("payload exceeds max buffer size; rejected", file=sys.stderr, flush=True)
            return
        try:
            command_string = str(raw, encoding="utf-8")
        except UnicodeDecodeError as error:
            print(repr(error), file=sys.stderr, flush=True)
            return
        socket = self.request
        print("command is: " + command_string, flush=True)
        if command_string == "quit_server":
            self.server.shutdown()
            self.server.close_flag = True
            print("Now quit server", flush=True)
        else:
            try:
                execute_str = json.loads(command_string)
                _validate_payload(execute_str)
                for execute_function, execute_return in execute_action(execute_str).items():
                    socket.sendto(str(execute_return).encode("utf-8"), self.client_address)
                    socket.sendto("\n".encode("utf-8"), self.client_address)
                socket.sendto("Return_Data_Over_JE".encode("utf-8"), self.client_address)
                socket.sendto("\n".encode("utf-8"), self.client_address)
            except Exception as error:
                print(repr(error), file=sys.stderr)
                try:
                    socket.sendto(str(error).encode("utf-8"), self.client_address)
                    socket.sendto("\n".encode("utf-8"), self.client_address)
                    socket.sendto("Return_Data_Over_JE".encode("utf-8"), self.client_address)
                    socket.sendto("\n".encode("utf-8"), self.client_address)
                except Exception as error:
                    print(repr(error))


class TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, server_address, request_handler_class):
        super().__init__(server_address, request_handler_class)
        self.close_flag: bool = False


def start_autocontrol_socket_server(host: str = "localhost", port: int = 9944):
    if len(sys.argv) == 2:
        host = sys.argv[1]
    elif len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    server = TCPServer((host, port), TCPServerHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return server
