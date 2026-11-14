"""Authenticated operations service; provider writes run only in the worker."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api import access
from app.api.intake import router as intake_router
from app.api.operations import router as operations_router
from app.api.operators import router
from app.config import SandboxGuardError, WebSettings, validate_product
from app.core import audit, db, signing
from app.core.operators import AuthenticationError
from app.logging_config import configure_logging


class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    data: dict[str, Any]


def verify_webhook(body: bytes, timestamp: str, signature: str, secret: str) -> None:
    if not secret or len(timestamp) > 16 or not timestamp.isascii() or not timestamp.isdigit():
        raise ValueError("invalid webhook authentication")
    expected = hmac.new(secret.encode(), timestamp.encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("invalid webhook authentication")
    if abs(time.time() * 1000 - int(timestamp)) > 300_000:
        raise ValueError("webhook timestamp outside tolerance")


def create_app() -> FastAPI:
    try:
        settings = WebSettings()
    except ValidationError:
        raise RuntimeError(
            "Invalid web configuration; check documented environment variables"
        ) from None
    database = db.Database(settings.app_db_path)
    rate_lock = threading.Lock()
    rate_window = [0.0, 0.0]

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            validate_product(settings)
            settings.check_startup(
                {**os.environ, "AWX_ENV": settings.awx_env, "AWX_BASE_URL": settings.awx_base_url}
            )
        except SandboxGuardError:
            raise RuntimeError(
                "Unsafe web configuration; check sandbox mode, origin and secret separation"
            ) from None
        configure_logging(
            {**os.environ, "AWX_WEBHOOK_SECRET": settings.awx_webhook_secret},
            level=settings.log_level,
        )
        database.connection()
        yield
        database.close()

    application = FastAPI(title="Wiretight", lifespan=lifespan, docs_url=None, redoc_url=None)
    passkeys = signing.Passkeys(
        rp_id=settings.webauthn_rp_id,
        origin=settings.webauthn_origin,
    )
    application.include_router(router(database, passkeys, settings))
    application.include_router(intake_router(database, passkeys, settings))

    application.include_router(operations_router(database, passkeys))
    static = Path(__file__).with_name("static")
    application.mount("/assets", StaticFiles(directory=static), name="assets")

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic errors normally echo input, including passwords or bank details.
        return JSONResponse(
            {
                "detail": [
                    {"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]}
                    for e in exc.errors()
                ]
            },
            status_code=422,
        )

    @application.exception_handler(AuthenticationError)
    async def invalid_session(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=401)

    @application.middleware("http")
    async def boundary(request: Request, call_next: Any) -> Any:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            try:
                if request.url.path == "/api/login":
                    access.same_origin(request, passkeys.origin)
                    if request.headers.get("content-type", "").split(";")[0] != "application/json":
                        return JSONResponse({"detail": "Login requires JSON"}, status_code=415)
                elif request.url.path.startswith("/api/"):
                    # Central protection runs before body validation or handlers,
                    # including for future routes that omit their local check.
                    access.identity(request, database, passkeys.origin, mutate=True)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if request.method in {"POST", "PUT", "PATCH"}:
            chunks = bytearray()
            async for chunk in request.stream():
                chunks.extend(chunk)
                if len(chunks) > (4194304 if request.url.path == "/api/evidence" else 262144):
                    return JSONResponse({"detail": "Request exceeds size limit"}, status_code=413)
            # Starlette's cached-request middleware replays this bounded body to
            # the downstream parser. Chunked requests get the same size limit.
            request._body = bytes(chunks)
        # Global bounded budget; never trust forwarded client headers.
        with rate_lock:
            now = time.monotonic()
            if now - rate_window[0] > 60:
                rate_window[:] = [now, 0]
            rate_window[1] += 1
            limited = rate_window[1] > 300
        if limited and request.url.path not in {"/health", "/ready"}:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        try:
            response = await call_next(request)
        except Exception as exc:
            logging.getLogger("wiretight").error(
                json.dumps(
                    {
                        "event": "request.failed",
                        "error_type": type(exc).__name__,
                    }
                )
            )
            response = JSONResponse({"detail": "Service unavailable; retry later"}, status_code=503)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        logging.getLogger("wiretight").info(
            {
                "event": "http.completed",
                "method": request.method,
                "route": getattr(request.scope.get("route"), "path", "unmatched"),
                "status": response.status_code,
            }
        )
        return response

    @application.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def setup_errors() -> list[str]:
        errors = []
        observation = (
            database.connection().execute("SELECT * FROM worker_health WHERE id=1").fetchone()
        )
        if not observation:
            errors.append("Worker credentials/config have not supplied a readiness observation")
        elif "credentials" in observation["detail"]:
            errors.append("Worker sandbox credentials or configuration are unavailable")
        else:
            checked = datetime.fromisoformat(observation["checked_at"])
            age = (datetime.now(UTC) - checked).total_seconds()
            if age < -120 or age > 120:
                errors.append("Worker readiness observation is stale or invalid")
            if not observation["ready"]:
                errors.append(
                    "Worker reports incomplete operational readiness: " + observation["detail"]
                )
        snapshot = (
            database.connection()
            .execute(
                "SELECT observed_at FROM provider_snapshot "
                "WHERE kind='BALANCES' AND subject='wallet'"
            )
            .fetchone()
        )
        if not snapshot:
            errors.append("No provider balance observation is available")
        else:
            observed = datetime.fromisoformat(snapshot["observed_at"])
            age = (datetime.now(UTC) - observed).total_seconds()
            if age < -120 or age > 120:
                errors.append("Provider balance observation is stale or invalid")
        if not settings.awx_webhook_secret:
            errors.append("Set AWX_WEBHOOK_SECRET for authenticated provider webhooks")
        return errors

    @application.get("/health")
    @application.get("/ready")
    def health() -> JSONResponse:
        errors = []
        try:
            database.connection().execute("SELECT 1").fetchone()
            errors.extend(setup_errors())
        except Exception:
            errors.append("Database unavailable")
        return JSONResponse(
            {"ready": not errors, "setup_errors": errors}, status_code=503 if errors else 200
        )

    @application.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (static / "index.html").read_text(encoding="utf-8")

    @application.post("/webhooks/airwallex")
    async def webhook(request: Request) -> dict[str, bool]:
        secret = settings.awx_webhook_secret
        if not secret:
            raise HTTPException(503, "Webhook secret is not configured")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 262144:
                raise HTTPException(413, "Webhook exceeds size limit")
        raw = bytes(body)
        try:
            verify_webhook(
                raw,
                request.headers.get("x-timestamp", ""),
                request.headers.get("x-signature", ""),
                secret,
            )
        except ValueError:
            raise HTTPException(400, "Webhook authentication failed") from None
        try:
            event = WebhookEvent.model_validate_json(raw)
        except ValidationError:
            raise HTTPException(400, "Invalid webhook event") from None
        digest = hashlib.sha256(raw).hexdigest()
        conn = database.connection()
        with db.transaction(conn):
            existing = conn.execute(
                "SELECT raw_sha256 FROM webhook_event WHERE event_id=?", (event.id,)
            ).fetchone()
            if existing:
                if existing["raw_sha256"] != digest:
                    raise HTTPException(409, "Event id reused with different content")
                return {"accepted": True, "duplicate": True}
            conn.execute(
                "INSERT INTO webhook_event(event_id,raw_sha256,received_at,enqueued_poll) "
                "VALUES(?,?,?,1)",
                (event.id, digest, datetime.now(UTC).isoformat()),
            )
            # Payload status never changes transfer state. Persist a poll hint
            # in the audit transaction; a worker must GET authoritative data.
            audit.append(conn, "webhook.received", {"event_id": event.id, "name": event.name})
        return {"accepted": True, "duplicate": False}

    return application


app = create_app()
