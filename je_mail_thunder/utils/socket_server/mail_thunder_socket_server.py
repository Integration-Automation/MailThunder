"""
The MailThunder socket server (port 9942): je_action_core's TCP action server running ``execute_action``,
with a payload check first (at most 256 actions of one or two elements, each named by a string).
"""
import sys
import warnings

from je_action_core import (
    ActionRequestHandler,
    ActionTCPServer,
    OversizePolicy,
    SocketServerSettings,
    start_action_socket_server,
)

from je_mail_thunder.utils.executor.action_executor import (
    ACTION_LIST_KEY,
    action_list_from_mapping,
    execute_action,
)

MAX_ACTIONS = 256
_MAX_ACTION_ELEMENTS = 2  # [name] or [name, payload]


def _validate_payload(payload):
    """
    Validate the decoded JSON payload structure before execution.
    Accepts either a list of action entries or a dict with a
    "mail_thunder" key (or the deprecated "auto_control") mapping to such a list. Each action entry must
    be a non-empty list whose first element is a string command name.
    """
    if isinstance(payload, dict):
        actions = action_list_from_mapping(payload)
        if not isinstance(actions, list):
            raise ValueError(f"payload dict must contain a '{ACTION_LIST_KEY}' list")
    elif isinstance(payload, list):
        actions = payload
    else:
        raise ValueError("payload must be a dict or list")
    if len(actions) == 0:
        raise ValueError("action list is empty")
    if len(actions) > MAX_ACTIONS:
        raise ValueError(f"action list exceeds max length {MAX_ACTIONS}")
    for entry in actions:
        if not isinstance(entry, list) or len(entry) == 0 or len(entry) > _MAX_ACTION_ELEMENTS:
            raise ValueError(f"invalid action entry: {entry!r}")
        if not isinstance(entry[0], str):
            raise ValueError(f"action command name must be str: {entry!r}")


# One slot in the sibling servers' range (AutoControl 9938, APITestka 9939, LoadDensity 9940,
# WebRunner 9941, FileAutomation 9943-9945); 9944 is FileAutomation's HTTP server.
DEFAULT_PORT = 9942


# The names this module has always exported.
TCPServer = ActionTCPServer
TCPServerHandler = ActionRequestHandler
_SETTINGS = SocketServerSettings(
    execute=execute_action,
    validate=_validate_payload,
    handled=(ValueError, OSError, TypeError),
    oversize=OversizePolicy.REJECT,
    log_info=lambda message: print(message, flush=True),
    log_error=lambda message: print(message, file=sys.stderr, flush=True),
)


def start_mail_thunder_socket_server(host: str = "localhost", port: int = DEFAULT_PORT) -> TCPServer:
    """Start the action server on a daemon thread and return it.

    It binds exactly ``host`` and ``port``; the command line is not consulted.
    """
    return start_action_socket_server(host, port, _SETTINGS)


def start_autocontrol_socket_server(host: str = "localhost", port: int = DEFAULT_PORT) -> TCPServer:
    """Deprecated alias of :func:`start_mail_thunder_socket_server`.

    The name was copied from AutoControl and says nothing about this package. It keeps working, with
    a ``DeprecationWarning``, for at least two further releases.
    """
    warnings.warn(
        "start_autocontrol_socket_server is deprecated; use start_mail_thunder_socket_server",
        DeprecationWarning, stacklevel=2)
    return start_mail_thunder_socket_server(host, port)
