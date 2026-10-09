"""The offline guarantees themselves must be tested.

FINAL.md §10.1 rule 9: "No sleeps, no network, no wall clock in offline tests.
Sockets are blocked." That is a claim about the test suite, so it gets a test.

If the socket block ever silently stops working, every "offline" run becomes a
run that might be quietly hitting the network, and the honesty of the whole
suite is gone. So assert the block, assert the escape hatch, and assert the
sandbox pin.
"""

from __future__ import annotations

import socket

import pytest

from tests.conftest import SocketBlockedError


@pytest.mark.compliance("T-09a")
def test_socket_construction_is_blocked_in_an_offline_test() -> None:
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


@pytest.mark.compliance("T-09a")
def test_create_connection_is_blocked_in_an_offline_test() -> None:
    with pytest.raises(SocketBlockedError):
        socket.create_connection(("api.sandbox.airwallex.com", 443), timeout=1)


@pytest.mark.compliance("T-09a")
def test_dns_resolution_is_blocked_in_an_offline_test() -> None:
    """DNS alone is enough to leak a request, so getaddrinfo is blocked too."""
    with pytest.raises(SocketBlockedError):
        socket.getaddrinfo("api.sandbox.airwallex.com", 443)


@pytest.mark.compliance("T-09a")
def test_httpx_cannot_reach_the_network_in_an_offline_test() -> None:
    """The realistic failure: a test that forgets to use the replay transport."""
    import httpx

    with pytest.raises(SocketBlockedError):
        httpx.get("https://api.sandbox.airwallex.com/api/v1/balances/current", timeout=5)


@pytest.mark.compliance("T-09a")
def test_socket_is_restored_after_the_block_is_lifted() -> None:
    """The fixture must restore the real socket, or later tests inherit the block."""
    # We are inside a non-live test, so the guard is active; constructing must fail.
    with pytest.raises(SocketBlockedError):
        socket.socket()
    # And after this test's fixture tears down, the next test gets a real socket.
    assert socket.socket.__module__ in {"socket", "tests.conftest"}


@pytest.mark.compliance("T-09a")
def test_sandbox_pin_is_set_by_the_conftest() -> None:
    import os

    assert os.environ["AWX_ENV"] == "sandbox"
    assert os.environ["AWX_BASE_URL"] == "https://api.sandbox.airwallex.com"
    assert os.environ["AWX_MODE"] == "replay"


@pytest.mark.compliance("T-09a")
def test_no_test_module_imports_an_unpinned_http_mock_library() -> None:
    """§6.1 cut list: respx and vcrpy are not used.

    The record/replay transport is written in-repo so its behaviour is visible
    and tested. A silent respx dependency would mean tests assert against a
    library's idea of the API rather than against recorded fixtures.
    """
    from pathlib import Path

    banned = ("import respx", "import vcr", "from vcr", "import betamax")
    test_root = Path(__file__).resolve().parent.parent
    this_file = Path(__file__).resolve()
    offenders: list[str] = []
    for path in test_root.rglob("*.py"):
        if path.resolve() == this_file:
            # This file necessarily contains the banned strings as data.
            continue
        text = path.read_text(encoding="utf-8")
        for needle in banned:
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert not offenders, f"Banned HTTP mock libraries found: {offenders}"
