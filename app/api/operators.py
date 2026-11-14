"""Authenticated operator and passkey routes. No money mutations here."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.core import db, operators, signing


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class CeremonyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ceremony_id: str = Field(min_length=1, max_length=36)
    credential: dict[str, Any]


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

    return routes
