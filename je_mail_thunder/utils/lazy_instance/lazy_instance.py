"""Module-level clients that connect on first use instead of at import.

``SMTPWrapper`` and ``IMAPWrapper`` open an SSL connection in their constructors. The package used
to build one of each at import time, so every ``import je_mail_thunder`` -- including the CLI that
only runs a ``print`` action -- dialled Gmail first, and on a machine without network the
constructor's ``OSError`` left the instance as ``None`` and the executor then failed the import
with ``AttributeError`` while reading methods off it.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


class LazyInstance:
    """Stand-in for a client built by ``factory`` the first time anything is read from it.

    Attribute reads, calls and ``with`` blocks are forwarded to the real client. A connection
    failure surfaces as the factory's exception at that first use, where the caller can handle it,
    and the next use tries again.
    """

    def __init__(self, factory: Callable[[], Any], name: str) -> None:
        self._factory = factory
        self._name = name
        self._instance: Optional[Any] = None

    @property
    def is_connected(self) -> bool:
        """True once the real client has been built."""
        return self._instance is not None

    def get(self) -> Any:
        """Return the real client, building (and connecting) it on the first call."""
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self.get(), attribute)

    def __enter__(self) -> Any:
        return self.get().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb) -> Any:
        return self.get().__exit__(exc_type, exc_val, exc_tb)

    def __repr__(self) -> str:
        state = "connected" if self.is_connected else "not connected yet"
        return f"<LazyInstance {self._name} ({state})>"


def deferred(lazy: LazyInstance, method_name: str) -> Callable[..., Any]:
    """Return a callable that looks ``method_name`` up on ``lazy`` only when it is called.

    Registering ``lazy.method`` directly would read the attribute -- and so connect -- at
    registration time, which is exactly what the lazy instance exists to avoid.
    """
    def call(*args: Any, **kwargs: Any) -> Any:
        return getattr(lazy.get(), method_name)(*args, **kwargs)

    call.__name__ = method_name
    call.__qualname__ = f"{lazy._name}.{method_name}"  # noqa: SLF001 - same module
    return call
