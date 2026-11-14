"""Product service. No imports from app.demo; unavailable operations fail closed."""

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
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.intake import router as intake_router
from app.api.operators import router
from app.config import SANDBOX_BASE_URL
from app.core import audit, db, signing
from app.core.operators import AuthenticationError


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
    database = db.Database(os.environ.get("APP_DB_PATH", "var/app.sqlite"))
    rate_lock = threading.Lock()
    rate_window = [0.0, 0.0]

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.connection()
        yield
        database.close()

    application = FastAPI(title="Wiretight", lifespan=lifespan, docs_url=None, redoc_url=None)
    passkeys = signing.Passkeys(
        rp_id=os.environ.get("WEBAUTHN_RP_ID", "localhost"),
        origin=os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:8000"),
    )
    application.include_router(router(database, passkeys))
    application.include_router(intake_router(database, passkeys))

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
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        return response

    def setup_errors() -> list[str]:
        errors = []
        if os.environ.get("AWX_ENV") != "sandbox":
            errors.append("Set AWX_ENV=sandbox")
        if os.environ.get("AWX_BASE_URL") != SANDBOX_BASE_URL:
            errors.append("Set AWX_BASE_URL to the documented sandbox URL")
        # The web process intentionally cannot see money credentials. Worker
        # readiness will eventually attest successful auth and current balances.
        if not os.environ.get("AWX_CLIENT_ID") or not os.environ.get("AWX_API_KEY"):
            errors.append("Airwallex credentials are not configured for this process")
        if os.environ.get("DEMO_MODE") or os.environ.get("APP_DEMO_TIMING", "").lower() in {
            "1",
            "true",
        }:
            errors.append("Demo settings are forbidden in the product service")
        if os.environ.get("AWX_MODE", "live") != "live":
            errors.append("Product requires AWX_MODE=live")
        errors.append(
            "Execution unavailable: durable worker and live guard verification are not implemented"
        )
        return errors

    @application.get("/health")
    @application.get("/ready")
    def health() -> JSONResponse:
        errors = setup_errors()
        try:
            database.connection().execute("SELECT 1").fetchone()
        except Exception:
            errors.append("Database unavailable")
        return JSONResponse(
            {"ready": not errors, "setup_errors": errors}, status_code=503 if errors else 200
        )

    @application.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (
            "<!doctype html><html><head><title>Wiretight setup</title></head><body>"
            "<h1>Wiretight</h1><p>Payment execution is unavailable while setup and approval "
            "controls are incomplete.</p><p><a href='/ready'>Readiness and setup errors</a></p>"
            "<p>No supplier or balance data has been loaded. See README.md for setup.</p>"
            "</body></html>"
        )

    @application.post("/webhooks/airwallex")
    async def webhook(request: Request) -> dict[str, bool]:
        secret = os.environ.get("AWX_WEBHOOK_SECRET", "")
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
