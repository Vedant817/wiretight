"""Environment settings and the sandbox-only guard.

FINAL.md §6.3 and §5.3. This module is the single place that decides whether
Wiretight is allowed to talk to Airwallex at all.

Three separate guarantees live here:

1. **Sandbox only.** The process refuses to start unless ``AWX_ENV`` is exactly
   ``sandbox`` and ``AWX_BASE_URL`` is exactly the sandbox host. There is no
   production URL anywhere in this file or in ``app/`` (§6.3, T-09a/T-09b).
2. **No ambient proxy.** The transport is built with ``trust_env=False``, so
   ``HTTPS_PROXY`` and friends cannot redirect traffic. T-09d asserts the
   transport actually saw the sandbox host with a proxy set in the environment.
3. **Process separation.** ``WebSettings`` loads the LLM key and never an
   Airwallex credential; ``WorkerSettings`` is the reverse. Each refuses to
   start if the other's secret is visible in its environment (T-R4e).

The guard is deliberately pure and synchronous so it can be unit-tested without
opening a socket: :func:`check_sandbox_guard` takes a mapping and returns, or
raises.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Final
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --------------------------------------------------------------------------
# The one and only Airwallex host this project may ever contact.
# FINAL.md §6.3: exact-match allowlist. A production URL must not appear
# anywhere in app/, so there is deliberately no production constant to compare
# against — a mismatch is simply "not the sandbox".
# --------------------------------------------------------------------------
SANDBOX_ENV_VALUE: Final[str] = "sandbox"
SANDBOX_BASE_URL: Final[str] = "https://api.sandbox.airwallex.com"

#: Clock skew against the server ``Date`` header that trips the kill switch (§4.15 r24).
CLOCK_SKEW_LIMIT_SECONDS: Final[int] = 120

#: Seconds before a quote's ``valid_to_at`` at which it is never booked (§4.15 r19).
QUOTE_SAFETY_MARGIN_SECONDS: Final[int] = 120

#: Basis points of FX drift a CONVERSION packet tolerates (§4.15 r20).
FX_DRIFT_BP: Final[int] = 25


class SandboxGuardError(RuntimeError):
    """Raised when the process is not allowed to run against the sandbox.

    Every refusal here is fatal and exits non-zero. There is no override flag:
    an environment variable that turns the guard off would defeat the guard.
    """


class ForeignSecretVisibleError(SandboxGuardError):
    """Raised when a process can see the *other* process's secret (T-R4e)."""


def check_sandbox_guard(env: Mapping[str, str]) -> str:
    """Validate that ``env`` points at the Airwallex sandbox and nowhere else.

    Returns the validated base URL. Raises :class:`SandboxGuardError` otherwise.

    The check is exact on both the environment name and the URL: a trailing
    slash, a different subdomain, or ``AWX_ENV=sandbox `` are all refused.
    """
    # Falsy, not just None: an empty `AWX_ENV=` in .env is as unset as a missing
    # one, and must be refused rather than silently treated as a value.
    awx_env = env.get("AWX_ENV")
    if not awx_env:
        raise SandboxGuardError(
            "AWX_ENV is not set. Refusing to start: Wiretight only ever talks to "
            "the Airwallex sandbox."
        )
    if awx_env != SANDBOX_ENV_VALUE:
        raise SandboxGuardError(
            f"AWX_ENV is {awx_env!r}, expected {SANDBOX_ENV_VALUE!r}. "
            "Wiretight refuses to start against anything but the sandbox."
        )

    base_url = env.get("AWX_BASE_URL")
    if not base_url:
        raise SandboxGuardError("AWX_BASE_URL is not set. Refusing to start.")
    if base_url != SANDBOX_BASE_URL:
        raise SandboxGuardError(
            f"AWX_BASE_URL is {base_url!r}, expected exactly {SANDBOX_BASE_URL!r}. "
            "Wiretight refuses to start against anything but the sandbox."
        )

    return base_url


def _require_absent(env: Mapping[str, str], names: tuple[str, ...], who: str) -> None:
    """Fail if any of ``names`` has a non-empty value in ``env``."""
    leaked = [n for n in names if env.get(n)]
    if leaked:
        raise ForeignSecretVisibleError(
            f"The {who} process can see {', '.join(sorted(leaked))}, which belongs to "
            "the other process. Refusing to start. Launch it with the secret unset "
            "(see the `env -u` wrappers in the Makefile)."
        )


#: Credentials that only the worker (executor + poller) may ever see.
AIRWALLEX_SECRET_VARS: Final[tuple[str, ...]] = ("AWX_CLIENT_ID", "AWX_API_KEY")

#: Credentials that only the web/ingest process may ever see.
LLM_SECRET_VARS: Final[tuple[str, ...]] = ("ANTHROPIC_API_KEY",)


class _BaseWiretightSettings(BaseSettings):
    """Shared, non-secret settings. Subclasses pick which key classes they load."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    awx_env: str = Field(default=SANDBOX_ENV_VALUE, alias="AWX_ENV")
    awx_base_url: str = Field(default=SANDBOX_BASE_URL, alias="AWX_BASE_URL")
    awx_mode: str = Field(default="live", alias="AWX_MODE")
    app_db_path: str = Field(default="var/app.sqlite", alias="APP_DB_PATH")
    app_halt_file: str = Field(default="var/HALT", alias="APP_HALT_FILE")
    app_display_tz: str = Field(default="Asia/Kolkata", alias="APP_DISPLAY_TZ")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("awx_mode")
    @classmethod
    def _known_mode(cls, value: str) -> str:
        if value not in {"replay", "live", "record"}:
            raise ValueError(f"AWX_MODE must be replay, live or record; got {value!r}")
        return value


class WebSettings(_BaseWiretightSettings):
    """Settings for ``make serve`` — the FastAPI web and ingest process.

    Loads the LLM key. Never loads an Airwallex credential: the web process must
    not be able to move money (§5.3).
    """

    # LLM: optional, off by default, never in the money path, masked input only.
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_provider: str = Field(default="anthropic", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    # Web surface.
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_policy_path: str = Field(default="policy.yaml", alias="APP_POLICY_PATH")
    app_key_dir: str = Field(default="var/keys", alias="APP_KEY_DIR")
    awx_webhook_secret: str = Field(default="", alias="AWX_WEBHOOK_SECRET", repr=False)
    app_policy_sig_path: str = Field(default="var/policy.sig.json", alias="APP_POLICY_SIG_PATH")
    signing_mode: str = Field(default="webauthn", alias="SIGNING_MODE")

    webauthn_rp_id: str = Field(default="localhost", alias="WEBAUTHN_RP_ID")
    webauthn_rp_name: str = Field(default="Wiretight", alias="WEBAUTHN_RP_NAME")
    webauthn_origin: str = Field(default="http://localhost:8000", alias="WEBAUTHN_ORIGIN")

    verify_account_enabled: bool = Field(default=False, alias="VERIFY_ACCOUNT_ENABLED")
    shadow_mode: bool = Field(default=False, alias="SHADOW_MODE")

    @field_validator("signing_mode")
    @classmethod
    def _known_signing_mode(cls, value: str) -> str:
        if value not in {"webauthn", "hmac_fallback"}:
            raise ValueError(f"SIGNING_MODE must be webauthn or hmac_fallback; got {value!r}")
        return value

    def check_startup(self, env: Mapping[str, str] | None = None) -> WebSettings:
        """Assert the guard passes and that no Airwallex credential is visible.

        Raises :class:`SandboxGuardError` or :class:`ForeignSecretVisibleError`.
        """
        environ = os.environ if env is None else env
        check_sandbox_guard(environ)
        _require_absent(environ, AIRWALLEX_SECRET_VARS, "web")
        return self


class WorkerSettings(_BaseWiretightSettings):
    """Settings for ``make worker`` — the executor and poller.

    Loads the Airwallex credentials. Never loads the LLM key: the executor must
    not be able to call a model while it holds the money credential (§5.3).
    """

    awx_client_id: str = Field(default="", alias="AWX_CLIENT_ID")
    app_key_dir: str = Field(default="var/keys", alias="APP_KEY_DIR")
    webauthn_rp_id: str = Field(default="localhost", alias="WEBAUTHN_RP_ID")
    webauthn_origin: str = Field(default="http://localhost:8000", alias="WEBAUTHN_ORIGIN")
    awx_api_key: str = Field(default="", alias="AWX_API_KEY")
    awx_login_as: str = Field(default="", alias="AWX_LOGIN_AS")
    awx_api_version: str = Field(default="", alias="AWX_API_VERSION")
    awx_min_account_api_version: str = Field(
        default="2025-06-30", alias="AWX_MIN_ACCOUNT_API_VERSION"
    )
    awx_request_id_namespace: str = Field(default="", alias="AWX_REQUEST_ID_NAMESPACE")
    awx_rps_global: int = Field(default=20, alias="AWX_RPS_GLOBAL")
    awx_rps_per_endpoint: int = Field(default=10, alias="AWX_RPS_PER_ENDPOINT")
    awx_max_concurrency: int = Field(default=10, alias="AWX_MAX_CONCURRENCY")
    awx_http_timeout_s: int = Field(default=20, alias="AWX_HTTP_TIMEOUT_S")

    app_policy_path: str = Field(default="policy.yaml", alias="APP_POLICY_PATH")
    app_policy_sig_path: str = Field(default="var/policy.sig.json", alias="APP_POLICY_SIG_PATH")
    app_audit_checkpoint_dir: str = Field(
        default="var/audit-checkpoints", alias="APP_AUDIT_CHECKPOINT_DIR"
    )
    app_audit_signing_key_path: str = Field(
        default="var/keys/audit_ed25519.pem", alias="APP_AUDIT_SIGNING_KEY_PATH"
    )

    signing_mode: str = Field(default="webauthn", alias="SIGNING_MODE")
    approver_hmac_keys_path: str = Field(
        default="var/keys/approvers.json", alias="APPROVER_HMAC_KEYS_PATH"
    )

    poll_interval_s: int = Field(default=2, alias="POLL_INTERVAL_S")
    poll_max_interval_s: int = Field(default=60, alias="POLL_MAX_INTERVAL_S")

    verify_account_enabled: bool = Field(default=False, alias="VERIFY_ACCOUNT_ENABLED")
    shadow_mode: bool = Field(default=False, alias="SHADOW_MODE")

    @field_validator("awx_mode")
    @classmethod
    def _live_mode_needs_keys(cls, value: str) -> str:
        return value

    def check_startup(self, env: Mapping[str, str] | None = None) -> WorkerSettings:
        """Assert the guard passes, that no LLM key is visible, and that live
        and record modes actually have credentials."""
        environ = os.environ if env is None else env
        check_sandbox_guard(environ)
        _require_absent(environ, LLM_SECRET_VARS, "worker")

        if self.awx_mode in {"live", "record"} and not (self.awx_client_id and self.awx_api_key):
            raise SandboxGuardError(
                f"AWX_MODE={self.awx_mode} needs AWX_CLIENT_ID and AWX_API_KEY in .env. "
                "See docs/NEEDS_HUMAN.md H1."
            )
        return self

    def has_credentials(self) -> bool:
        return bool(self.awx_client_id and self.awx_api_key)


def _redact(value: str) -> str:
    """Mask an identifier for logs: keep the last 4, mask the rest (§6.3)."""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * max(0, len(value) - 4) + value[-4:]


def log_settings_safely(settings: Any) -> dict[str, Any]:
    """Return a dict safe to log: every secret replaced by a mask.

    Logs mask accounts as ``•••• 4821``. No key is ever printed, logged or echoed.
    """
    out: dict[str, Any] = {}
    for name, value in settings.model_dump().items():
        if any(part in name for part in ("key", "secret", "password", "token", "client_id")):
            out[name] = "[REDACTED]" if value else ""
        else:
            out[name] = value
    return out


def validate_product(settings: WebSettings | WorkerSettings) -> None:
    """No permissive recording modes, shortened controls or unsafe browser origins."""
    check_sandbox_guard({"AWX_ENV": settings.awx_env, "AWX_BASE_URL": settings.awx_base_url})
    if settings.awx_mode != "live" or settings.signing_mode != "webauthn" or settings.shadow_mode:
        raise SandboxGuardError("Product requires live sandbox mode and WebAuthn")
    environment = {**dotenv_values(".env"), **os.environ}
    if environment.get("DEMO_MODE") or environment.get("APP_DEMO_TIMING"):
        raise SandboxGuardError("Recording settings are forbidden in the product")
    origin = urlsplit(settings.webauthn_origin)
    if (
        origin.scheme not in {"http", "https"}
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.query
        or origin.fragment
        or origin.path not in {"", "/"}
        or origin.hostname != settings.webauthn_rp_id
        or (origin.scheme != "https" and origin.hostname not in {"localhost", "127.0.0.1"})
    ):
        raise SandboxGuardError("Configure an HTTPS origin and matching WebAuthn RP, or localhost")
    if settings.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise SandboxGuardError("Invalid LOG_LEVEL")
    if isinstance(settings, WebSettings) and not 1 <= settings.app_port <= 65535:
        raise SandboxGuardError("Invalid APP_PORT")
    if isinstance(settings, WorkerSettings) and (
        not 1 <= settings.poll_interval_s <= 60 or not 1 <= settings.awx_http_timeout_s <= 120
    ):
        raise SandboxGuardError("Invalid worker polling interval or timeout")
