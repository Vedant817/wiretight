"""Authenticated operator and passkey routes. No money mutations here."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.core import (
    callbacks,
    db,
    killswitch,
    operators,
    record_signing,
    runtime_halt,
    runtime_policy,
    signing,
)
from app.core.policy import PolicyError


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class CeremonyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ceremony_id: str = Field(min_length=1, max_length=36)
    credential: dict[str, Any]


class CallbackFinish(CeremonyBody):
    callback: callbacks.CallbackInput


class ReasonBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


class ClearFinish(CeremonyBody):
    reason: str = Field(min_length=1, max_length=1000)


def router(database: db.Database, passkeys: signing.Passkeys) -> APIRouter:
    routes = APIRouter(prefix="/api")

    def same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin and origin != passkeys.origin:
            raise HTTPException(403, "Request origin is not allowed")

    def identity(request: Request, *, mutate: bool = False) -> operators.Session:
        same_origin(request)
        try:
            return operators.authenticate(
                database.connection(),
                request.cookies.get("wt_session", ""),
                csrf=request.headers.get("x-csrf-token", "") if mutate else None,
            )
        except operators.AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from None

    @routes.post("/login")
    def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
        same_origin(request)
        try:
            token, csrf = operators.login(
                database.connection(),
                email=body.email,
                password=body.password,
                source=request.client.host if request.client else "unknown",
            )
        except operators.AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from None
        secure = passkeys.origin.startswith("https://")
        response.set_cookie(
            "wt_session",
            token,
            max_age=28800,
            httponly=True,
            secure=secure,
            samesite="strict",
            path="/",
        )
        response.set_cookie(
            "wt_csrf",
            csrf,
            max_age=28800,
            httponly=False,
            secure=secure,
            samesite="strict",
            path="/",
        )
        return {"signed_in": True, "csrf_token": csrf}

    @routes.get("/session")
    def session(request: Request) -> dict[str, Any]:
        user = identity(request)
        row = (
            database.connection()
            .execute("SELECT public_key FROM user WHERE id=?", (user.user_id,))
            .fetchone()
        )
        return {
            "user_id": user.user_id,
            "name": user.name,
            "role": user.role,
            "passkey_registered": bool(row and row["public_key"]),
        }

    @routes.post("/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        operators.logout(database.connection(), identity(request, mutate=True))
        response.delete_cookie("wt_session")
        response.delete_cookie("wt_csrf")
        return {"signed_out": True}

    @routes.post("/passkeys/register/options")
    def registration_options(request: Request) -> dict[str, Any]:
        try:
            return passkeys.begin(database.connection(), identity(request, mutate=True))
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.post("/passkeys/finish")
    def finish(body: CeremonyBody, request: Request) -> dict[str, bool]:
        try:
            passkeys.finish(
                database.connection(),
                identity(request, mutate=True),
                ceremony_id=body.ceremony_id,
                credential=body.credential,
            )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"verified": True}

    @routes.get("/approvals")
    def approvals(request: Request) -> list[dict[str, Any]]:
        identity(request)
        rows = (
            database.connection()
            .execute(
                "SELECT id,kind,sha256,tier,required_approvers,expires_at,state,canonical_json "
                "FROM approval_packet ORDER BY created_at DESC LIMIT 100",
            )
            .fetchall()
        )
        return [dict(row) for row in rows]

    @routes.post("/approvals/{packet_id}/options")
    def approval_options(packet_id: str, request: Request) -> dict[str, Any]:
        try:
            return passkeys.begin(
                database.connection(), identity(request, mutate=True), packet_id=packet_id
            )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None

    def current_policy() -> tuple[Any, dict[str, Any]]:
        try:
            return runtime_policy.validated_policy(
                database.connection(), os.environ.get("APP_POLICY_PATH", "policy.yaml")
            )
        except (OSError, ValueError, PolicyError):
            raise HTTPException(
                503, "Policy missing, invalid, or inconsistent with the installation roster"
            ) from None

    @routes.get("/policy")
    def policy_view(request: Request) -> dict[str, Any]:
        identity(request)
        policy, _ = current_policy()
        signatures = (
            database.connection()
            .execute(
                "SELECT COUNT(*) FROM signed_record WHERE purpose='POLICY' AND subject_id=?",
                (policy.sha256,),
            )
            .fetchone()[0]
        )
        try:
            runtime_policy.load_runtime_policy(database.connection(), policy.path, passkeys)
            verified = True
        except signing.SigningError:
            verified = False
        return {
            "sha256": policy.sha256,
            "policy": policy.policy,
            "signatures": signatures,
            "verified": verified,
        }

    @routes.post("/policy/options")
    def policy_options(request: Request) -> dict[str, Any]:
        session = identity(request, mutate=True)
        policy, record = current_policy()
        try:
            return record_signing.begin_record(
                database.connection(),
                session,
                passkeys,
                purpose="POLICY",
                subject_id=policy.sha256,
                record=record,
            )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.post("/policy/finish")
    def policy_finish(body: CeremonyBody, request: Request) -> dict[str, bool]:
        session = identity(request, mutate=True)
        policy, record = current_policy()
        try:
            record_signing.finish_record(
                database.connection(),
                session,
                passkeys,
                purpose="POLICY",
                subject_id=policy.sha256,
                record=record,
                ceremony_id=body.ceremony_id,
                credential=body.credential,
            )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"signed": True}

    @routes.get("/bank-changes")
    def bank_changes(request: Request) -> list[dict[str, Any]]:
        identity(request)
        rows = (
            database.connection()
            .execute(
                "SELECT id,vendor_id,received_at,proposed_masked,proposed_fingerprint,status "
                "FROM payee_change_request ORDER BY received_at DESC LIMIT 100",
            )
            .fetchall()
        )
        return [dict(row) for row in rows]

    @routes.post("/bank-changes/{request_id}/callback/options")
    def callback_options(
        request_id: str, body: callbacks.CallbackInput, request: Request
    ) -> dict[str, Any]:
        try:
            return callbacks.begin_callback(
                database.connection(),
                identity(request, mutate=True),
                passkeys,
                request_id=request_id,
                body=body,
            )
        except (ValueError, PermissionError, signing.SigningError):
            raise HTTPException(
                409, "Callback refused: check independent contact, recorder, readback and timing"
            ) from None

    @routes.post("/bank-changes/{request_id}/callback/finish")
    def callback_finish(request_id: str, body: CallbackFinish, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        policy, _ = current_policy()
        try:
            callback_id = callbacks.apply_callback(
                database.connection(),
                session,
                passkeys,
                request_id=request_id,
                body=body.callback,
                ceremony_id=body.ceremony_id,
                credential=body.credential,
                cooling_hours=policy.policy["bank_change"]["cooling_off_hours"],
            )
        except (ValueError, PermissionError, signing.SigningError):
            raise HTTPException(
                409, "Callback changed, expired, conflicted or failed signature verification"
            ) from None
        return {"callback_id": callback_id}

    @routes.get("/halt")
    def halt_view(request: Request) -> dict[str, Any]:
        identity(request)
        state = killswitch.load(database.connection(), os.environ.get("APP_HALT_FILE", "var/HALT"))
        return {
            "halted": state.is_halted(),
            "trip_id": state.active_trip_id(),
            "reason": state.reason_text(),
        }

    @routes.post("/halt")
    def halt_now(body: ReasonBody, request: Request) -> dict[str, str]:
        identity(request, mutate=True)
        record = killswitch.trip(database.connection(), body.reason, origin="human")
        return {"trip_id": record.id}

    @routes.post("/halt/clear/options")
    def clear_options(body: ReasonBody, request: Request) -> dict[str, Any]:
        try:
            with database.transaction() as conn:
                subject, record = runtime_halt.clear_record(conn, body.reason)
                return record_signing.begin_record(
                    conn,
                    identity(request, mutate=True),
                    passkeys,
                    purpose="CLEAR",
                    subject_id=subject,
                    record=record,
                )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.post("/halt/clear/finish")
    def clear_finish(body: ClearFinish, request: Request) -> dict[str, bool]:
        try:
            cleared = runtime_halt.finish_clear(
                database.connection(),
                identity(request, mutate=True),
                passkeys,
                reason=body.reason,
                ceremony_id=body.ceremony_id,
                credential=body.credential,
            )
        except signing.SigningError as exc:
            raise HTTPException(409, str(exc)) from None
        return {
            "database_halt_cleared": cleared,
            "local_halt_marker_present": os.path.lexists(
                os.environ.get("APP_HALT_FILE", "var/HALT")
            ),
        }

    return routes
