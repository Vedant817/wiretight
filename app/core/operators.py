"""Locally provisioned operators, scrypt passwords, revocable bounded sessions.

No default identities/passwords. CLI provisioning is an administrative local-shell
operation. HTTP never creates users or changes their roles.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core import audit, db

_PASSWORD_SLOTS = threading.BoundedSemaphore(4)


class AuthenticationError(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str) -> str:
    if not 14 <= len(password) <= 256:
        raise ValueError("Password must contain 14 to 256 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=67108864)
    return f"scrypt-v1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    if len(password) > 256:
        return False
    if not _PASSWORD_SLOTS.acquire(blocking=False):
        raise AuthenticationError("Login busy; try again shortly")
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt-v1":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=1, maxmem=67108864
        )
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False
    finally:
        _PASSWORD_SLOTS.release()


def provision(conn: db.Connection, *, name: str, email: str, role: str, password: str) -> str:
    email = email.strip().lower()
    if not name.strip() or len(name) > 120 or len(email) > 254 or "@" not in email:
        raise ValueError("Provide a name and valid operator email")
    if role not in {"approver", "ops"}:
        raise ValueError("Role must be approver or ops")
    encoded = password_hash(password)
    user_id = str(uuid4())
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO user(id,name,email,role,created_at) VALUES(?,?,?,?,?)",
            (user_id, name.strip(), email, role, utcnow().isoformat()),
        )
        conn.execute(
            "INSERT INTO operator_auth(user_id,password_hash) VALUES(?,?)", (user_id, encoded)
        )
        audit.append(conn, "operator.provisioned", {"user_id": user_id, "role": role})
    return user_id


@dataclass(frozen=True)
class Session:
    user_id: str
    name: str
    role: str
    token_hash: str


def login(conn: db.Connection, *, email: str, password: str, source: str) -> tuple[str, str]:
    """DB-backed per-source and per-account limits survive app restarts."""
    now = utcnow()
    buckets = [digest("source:" + source), digest("email:" + email.strip().lower())]
    # Unknown users take the same expensive password path to limit enumeration.
    dummy = "scrypt-v1$" + "00" * 16 + "$" + "00" * 64
    row = conn.execute(
        "SELECT u.id,a.password_hash,a.enabled FROM user u JOIN operator_auth a ON a.user_id=u.id "
        "WHERE u.email=?",
        (email.strip().lower(),),
    ).fetchone()
    with db.transaction(conn):
        for bucket in buckets:
            limit = conn.execute(
                "SELECT failures,reset_at FROM login_attempt WHERE bucket=?", (bucket,)
            ).fetchone()
            if limit and limit["reset_at"] > now.isoformat() and limit["failures"] >= 10:
                raise AuthenticationError("Login temporarily unavailable; try again later")
    valid = verify_password(password, row["password_hash"] if row else dummy)
    with db.transaction(conn):
        # Check again under the writer lock: concurrent requests cannot all pass
        # the initial rate check then bypass the stored failure threshold.
        for bucket in buckets:
            limit = conn.execute(
                "SELECT failures,reset_at FROM login_attempt WHERE bucket=?", (bucket,)
            ).fetchone()
            if limit and limit["reset_at"] > now.isoformat() and limit["failures"] >= 10:
                raise AuthenticationError("Login temporarily unavailable; try again later")
        fresh = (
            conn.execute(
                "SELECT password_hash,enabled FROM operator_auth WHERE user_id=?", (row["id"],)
            ).fetchone()
            if row
            else None
        )
        if (
            not valid
            or not row
            or not fresh
            or not fresh["enabled"]
            or fresh["password_hash"] != row["password_hash"]
        ):
            for bucket in buckets:
                conn.execute(
                    "INSERT INTO login_attempt(bucket,failures,reset_at) VALUES(?,1,?) "
                    "ON CONFLICT(bucket) DO UPDATE SET "
                    "failures=CASE WHEN reset_at<=? THEN 1 ELSE failures+1 END, "
                    "reset_at=CASE WHEN reset_at<=? THEN excluded.reset_at ELSE reset_at END",
                    (
                        bucket,
                        (now + timedelta(minutes=15)).isoformat(),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            audit.append(conn, "operator.login_failed", {"source_hash": buckets[0]})
        else:
            # Do not reset the source bucket: a successful login must not erase
            # a password spray against other accounts from the same address.
            conn.execute("DELETE FROM login_attempt WHERE bucket=?", (buckets[1],))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO operator_session(token_hash,user_id,csrf_hash,created_at,expires_at) "
                "VALUES(?,?,?,?,?)",
                (
                    digest(token),
                    row["id"],
                    digest(csrf),
                    now.isoformat(),
                    (now + timedelta(hours=8)).isoformat(),
                ),
            )
            audit.append(conn, "operator.login", {"user_id": row["id"]})
            return token, csrf
    raise AuthenticationError("Invalid email or password")


def authenticate(conn: db.Connection, token: str, *, csrf: str | None = None) -> Session:
    if not token or len(token) > 256:
        raise AuthenticationError("Sign in required")
    row = conn.execute(
        "SELECT u.id,u.name,u.role,s.token_hash,s.csrf_hash FROM operator_session s "
        "JOIN user u ON u.id=s.user_id JOIN operator_auth a ON a.user_id=u.id "
        "WHERE s.token_hash=? AND s.expires_at>? AND a.enabled=1",
        (digest(token), utcnow().isoformat()),
    ).fetchone()
    if not row:
        raise AuthenticationError("Session expired or revoked; sign in again")
    if csrf is not None and not hmac.compare_digest(row["csrf_hash"], digest(csrf)):
        raise AuthenticationError("Invalid request token")
    return Session(row["id"], row["name"], row["role"], row["token_hash"])


def logout(conn: db.Connection, session: Session) -> None:
    with db.transaction(conn):
        # Drop pending ceremonies before deleting their parent session.
        conn.execute(
            "DELETE FROM signing_challenge WHERE session_hash=? AND consumed_at IS NULL",
            (session.token_hash,),
        )
        # Consumed ceremonies remain as evidence. Expiring a session revokes it
        # without deleting the foreign-key target.
        conn.execute(
            "UPDATE operator_session SET expires_at=? WHERE token_hash=?",
            (utcnow().isoformat(), session.token_hash),
        )
        audit.append(conn, "operator.logout", {"user_id": session.user_id})


def require_active(conn: db.Connection, session: Session) -> None:
    row = conn.execute(
        "SELECT u.role FROM operator_session s JOIN operator_auth a ON a.user_id=s.user_id "
        "JOIN user u ON u.id=s.user_id WHERE s.token_hash=? AND s.user_id=? "
        "AND a.enabled=1 AND s.expires_at>?",
        (session.token_hash, session.user_id, utcnow().isoformat()),
    ).fetchone()
    if not row or row["role"] != session.role:
        raise AuthenticationError("Session expired or revoked; sign in again")


def disable(conn: db.Connection, email: str) -> None:
    with db.transaction(conn):
        row = conn.execute("SELECT id FROM user WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row:
            raise ValueError("Unknown operator")
        conn.execute("UPDATE operator_auth SET enabled=0 WHERE user_id=?", (row["id"],))
        conn.execute(
            "UPDATE operator_session SET expires_at=? WHERE user_id=?",
            (utcnow().isoformat(), row["id"]),
        )
        audit.append(conn, "operator.disabled", {"user_id": row["id"]})
