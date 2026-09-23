"""The SMTP and IMAP clients connect on first use, never at import (progress.md #6).

Before, importing the package dialled smtp.gmail.com and imap.gmail.com; offline, the constructor's
OSError left the instances as None and the executor's import then raised AttributeError.
"""
import os
import subprocess  # nosec B404 - the import is exercised in a fresh interpreter
import sys
from pathlib import Path

import pytest

from je_mail_thunder.utils.lazy_instance.lazy_instance import LazyInstance, deferred

REPO_ROOT = Path(__file__).resolve().parents[2]

_OFFLINE_IMPORT = (
    "import socket\n"
    "attempts = []\n"
    "def offline(*args, **kwargs):\n"
    "    attempts.append(args)\n"
    "    raise OSError('network unreachable (test)')\n"
    "socket.create_connection = offline\n"
    "import je_mail_thunder\n"
    "from je_mail_thunder.utils.executor.action_executor import Executor\n"
    "Executor()\n"
    "print(len(attempts))\n"
)


class _Client:
    built = 0

    def __init__(self):
        type(self).built += 1
        self.value = "ready"

    def greet(self, name):
        return f"hello {name}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.fixture(autouse=True)
def _reset_counter():
    _Client.built = 0


def test_importing_offline_neither_connects_nor_fails(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO_ROOT), env.get("PYTHONPATH")]))
    result = subprocess.run(  # nosec B603  # nosemgrep - fixed interpreter, test-controlled code
        [sys.executable, "-c", _OFFLINE_IMPORT],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0"


def test_client_is_built_on_first_attribute_read_and_only_once():
    lazy = LazyInstance(_Client, "client")
    assert _Client.built == 0
    assert not lazy.is_connected
    assert lazy.value == "ready"
    assert lazy.greet("mail") == "hello mail"
    assert _Client.built == 1
    assert lazy.is_connected


def test_a_failed_build_raises_at_use_and_is_retried():
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("first connection refused")
        return _Client()

    lazy = LazyInstance(flaky, "client")
    with pytest.raises(OSError):
        lazy.get()
    assert lazy.value == "ready"
    assert len(attempts) == 2


def test_deferred_does_not_build_until_called():
    lazy = LazyInstance(_Client, "client")
    greet = deferred(lazy, "greet")
    assert _Client.built == 0
    assert greet("later") == "hello later"
    assert _Client.built == 1
    assert greet.__name__ == "greet"


def test_with_block_is_forwarded():
    lazy = LazyInstance(_Client, "client")
    with lazy as client:
        assert isinstance(client, _Client)


def test_package_instances_are_lazy():
    from je_mail_thunder import imap_instance, smtp_instance

    assert isinstance(smtp_instance, LazyInstance)
    assert isinstance(imap_instance, LazyInstance)
