"""T-R4e: the two processes must not be able to see each other's secret.

FINAL.md §5.3: ``WebSettings`` loads ``LLM_*`` / ``ANTHROPIC_API_KEY`` and never
``AWX_CLIENT_ID`` / ``AWX_API_KEY``. ``WorkerSettings`` loads ``AWX_*`` and never
the LLM key. Each process **refuses to start** if the other's secret is visible.

This is logical separation on one laptop, not OS isolation. The README says so.
"""

from __future__ import annotations

import pytest

from app.config import (
    AIRWALLEX_SECRET_VARS,
    LLM_SECRET_VARS,
    ForeignSecretVisibleError,
    SandboxGuardError,
    WebSettings,
    WorkerSettings,
    check_sandbox_guard,
)

_SANDBOX_URL = "https://api.sandbox.airwallex.com"
SANDBOX_ENV = {"AWX_ENV": "sandbox", "AWX_BASE_URL": _SANDBOX_URL}


@pytest.mark.compliance("T-R4e")
def test_web_process_refuses_to_start_when_it_sees_the_airwallex_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A web process holding AWX_API_KEY must refuse to start."""
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setenv("AWX_API_KEY", "would-be-a-real-key")

    with pytest.raises(ForeignSecretVisibleError, match="web process"):
        WebSettings().check_startup()


@pytest.mark.compliance("T-R4e")
def test_worker_process_refuses_to_start_when_it_sees_the_llm_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A worker process holding ANTHROPIC_API_KEY must refuse to start.

    The worker is the only component that can move money. It must not be able to
    call a model while it holds the Airwallex credential.
    """
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "would-be-a-real-key")

    with pytest.raises(ForeignSecretVisibleError, match="worker process"):
        WorkerSettings().check_startup()


@pytest.mark.compliance("T-R4e")
@pytest.mark.parametrize("secret_name", AIRWALLEX_SECRET_VARS)
def test_every_airwallex_secret_is_blocked_from_the_web_process(
    monkeypatch: pytest.MonkeyPatch, secret_name: str
) -> None:
    """Not just the API key: the client id leaks just as badly."""
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setenv(secret_name, "would-be-a-real-key")

    with pytest.raises(ForeignSecretVisibleError):
        WebSettings().check_startup()


@pytest.mark.compliance("T-R4e")
@pytest.mark.parametrize("secret_name", LLM_SECRET_VARS)
def test_every_llm_secret_is_blocked_from_the_worker_process(
    monkeypatch: pytest.MonkeyPatch, secret_name: str
) -> None:
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setenv(secret_name, "would-be-a-real-key")

    with pytest.raises(ForeignSecretVisibleError):
        WorkerSettings().check_startup()


@pytest.mark.compliance("T-R4e")
def test_empty_string_is_not_treated_as_a_leaked_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ANTHROPIC_API_KEY=` in .env is a placeholder, not a leak.

    pydantic-settings maps an empty var to "", and that must not trip the guard,
    or the default `.env.example` would make the app unstartable.
    """
    monkeypatch.setenv("AWX_ENV", "sandbox")
    monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("LLM_ENABLED", "false")

    WorkerSettings().check_startup()  # must not raise


@pytest.mark.compliance("T-R4e")
def test_web_settings_never_exposes_an_airwallex_field() -> None:
    """The web settings object must not even have the attribute to leak."""
    fields = set(WebSettings.model_fields)
    assert not fields & set(AIRWALLEX_SECRET_VARS)


@pytest.mark.compliance("T-R4e")
def test_worker_settings_never_exposes_an_llm_field() -> None:
    fields = set(WorkerSettings.model_fields)
    assert not fields & set(LLM_SECRET_VARS)


#: A refused (env, expected-message) pair. The guard is exact on both variables:
#: case, whitespace, scheme and a trailing slash are all refused.
_REFUSED: tuple[tuple[dict[str, str], str], ...] = (
    ({}, "AWX_ENV is not set"),
    ({"AWX_ENV": ""}, "AWX_ENV is not set"),
    # AWX_ENV overrides come *after* the spread, so the bad value wins.
    ({**SANDBOX_ENV, "AWX_ENV": "production"}, "expected 'sandbox'"),
    ({**SANDBOX_ENV, "AWX_ENV": "Sandbox"}, "expected 'sandbox'"),
    ({**SANDBOX_ENV, "AWX_ENV": "sandbox "}, "expected 'sandbox'"),
    ({"AWX_ENV": "sandbox", "AWX_BASE_URL": ""}, "Refusing to start"),
    # A base URL that is not the sandbox, character for character.
    (
        {"AWX_ENV": "sandbox", "AWX_BASE_URL": _SANDBOX_URL.replace("https:", "http:")},
        "expected exactly",
    ),
    (
        {"AWX_ENV": "sandbox", "AWX_BASE_URL": _SANDBOX_URL.removeprefix("https://api.")},
        "expected exactly",
    ),
    ({"AWX_ENV": "sandbox", "AWX_BASE_URL": _SANDBOX_URL + "/"}, "expected exactly"),
)


@pytest.mark.compliance("T-09b")
@pytest.mark.parametrize(("env", "expected"), _REFUSED)
@pytest.mark.compliance("T-09")
def test_sandbox_guard_is_exact_on_both_variables(env: dict[str, str], expected: str) -> None:
    """Case, whitespace and trailing slash are all refused.

    There is no production URL constant to compare against: a mismatch simply
    means "not the sandbox", so no production host can appear in app/ at all.
    """
    with pytest.raises(SandboxGuardError, match=expected):
        check_sandbox_guard(env)


@pytest.mark.compliance("T-09a")
def test_sandbox_guard_accepts_exactly_the_sandbox_pair() -> None:
    assert check_sandbox_guard(SANDBOX_ENV) == "https://api.sandbox.airwallex.com"


@pytest.mark.compliance("T-09a")
def test_live_and_record_modes_require_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live run without keys must fail at startup, not on the first API call."""
    for mode in ("live", "record"):
        monkeypatch.setenv("AWX_ENV", "sandbox")
        monkeypatch.setenv("AWX_BASE_URL", "https://api.sandbox.airwallex.com")
        monkeypatch.setenv("AWX_MODE", mode)
        monkeypatch.setenv("AWX_CLIENT_ID", "")
        monkeypatch.setenv("AWX_API_KEY", "")

        with pytest.raises(SandboxGuardError, match="needs AWX_CLIENT_ID and AWX_API_KEY"):
            WorkerSettings().check_startup()
