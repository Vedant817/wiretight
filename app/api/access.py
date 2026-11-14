"""Shared cookie, origin and CSRF boundary for all operator routes."""

from fastapi import HTTPException, Request

from app.core import db, operators


def same_origin(request: Request, origin: str) -> None:
    supplied = request.headers.get("origin")
    if supplied and supplied != origin:
        raise HTTPException(403, "Request origin is not allowed")


def identity(
    request: Request, database: db.Database, origin: str, *, mutate: bool = False
) -> operators.Session:
    same_origin(request, origin)
    try:
        return operators.authenticate(
            database.connection(),
            request.cookies.get("wt_session", ""),
            csrf=request.headers.get("x-csrf-token", "") if mutate else None,
        )
    except operators.AuthenticationError as exc:
        raise HTTPException(401, str(exc)) from None
