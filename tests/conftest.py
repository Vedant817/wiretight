"""Root conftest: the sandbox pin and the socket block.

FINAL.md §6.2: ``conftest.py`` blocks sockets unless a test is marked
``@pytest.mark.live``, and pins ``AWX_ENV=sandbox``.

FINAL.md §10.1 rule 9: no sleeps, no network, no wall clock in offline tests.
The socket block is what makes that enforceable rather than aspirational — a
test that quietly reaches the internet fails loudly instead of passing on a
laptop that happens to be online.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The sandbox pin, set before anything imports app.config.
os.environ["AWX_ENV"] = "sandbox"
os.environ["AWX_BASE_URL"] = "https://api.sandbox.airwallex.com"
# Offline by default. `make test-live` overrides this per session.
os.environ.setdefault("AWX_MODE", "replay")


class SocketBlockedError(RuntimeError):
    """A test tried to open a network socket in an offline run."""


def _blocked(*args: object, **kwargs: object) -> None:
    raise SocketBlockedError(
        "Network access is blocked in offline tests. A test that needs the real "
        "sandbox must be marked @pytest.mark.live (FINAL.md §10.2). "
        f"It was called with: {args!r}"
    )


@pytest.fixture(autouse=True)
def _no_sockets(request: pytest.FixtureRequest) -> Iterator[None]:
    """Block every outbound socket for tests that are not marked ``live``."""
    if request.node.get_closest_marker("live") is not None:
        yield
        return

    real_socket = socket.socket
    real_create_connection = socket.create_connection
    real_getaddrinfo = socket.getaddrinfo

    def guard(*args: object, **kwargs: object) -> None:
        _blocked(*args, **kwargs)

    socket.socket = guard  # type: ignore[assignment,misc]
    socket.create_connection = guard  # type: ignore[assignment]
    socket.getaddrinfo = guard  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = real_socket  # type: ignore[assignment,misc]
        socket.create_connection = real_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = real_getaddrinfo  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _isolated_var_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point every writable path at ``tmp_path`` so tests never touch real state.

    Keeps the local DB, HALT file, audit checkpoints and key material inside the
    test's own directory. Nothing escapes into ``var/``.
    """
    var = tmp_path / "var"
    var.mkdir()
    (var / "keys").mkdir()

    monkeypatch.setenv("APP_DB_PATH", str(var / "app.sqlite"))
    monkeypatch.setenv("APP_HALT_FILE", str(var / "HALT"))
    monkeypatch.setenv("APP_AUDIT_CHECKPOINT_DIR", str(var / "audit-checkpoints"))
    monkeypatch.setenv("APP_AUDIT_SIGNING_KEY_PATH", str(var / "keys" / "audit_ed25519.pem"))
    monkeypatch.setenv("APPROVER_HMAC_KEYS_PATH", str(var / "keys" / "approvers.json"))
    monkeypatch.setenv("APP_POLICY_SIG_PATH", str(var / "policy.sig.json"))

    # Never inherit a developer's real credentials into a test run.
    for name in ("AWX_CLIENT_ID", "AWX_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    yield var
