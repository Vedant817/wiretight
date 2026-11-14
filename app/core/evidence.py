"""Encrypted source evidence. Uploading a file makes no assertion about its truth."""

from __future__ import annotations

import hashlib
import re

from app.core import audit, db, operators
from app.core.bank_details import DetailVault

MAX_BYTES = 4 * 1024 * 1024
MEDIA_TYPES = {"text/plain", "application/json", "message/rfc822", "application/pdf"}


class EvidenceError(ValueError):
    pass


def require(conn: db.Connection, digest: str) -> db.sqlite3.Row:
    row: db.sqlite3.Row | None = conn.execute(
        "SELECT * FROM evidence_file WHERE sha256=?", (digest,)
    ).fetchone()
    if not row:
        raise EvidenceError("Upload the source evidence first")
    return row


def store(
    conn: db.Connection,
    vault: DetailVault,
    session: operators.Session,
    *,
    content: bytes,
    filename: str,
    media_type: str,
) -> dict[str, str | int]:
    if not content or len(content) > MAX_BYTES:
        raise EvidenceError("Evidence must contain 1 to 4194304 bytes")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,159}", filename):
        raise EvidenceError("Use a simple filename without path separators")
    if media_type not in MEDIA_TYPES:
        raise EvidenceError("Evidence must be plain text, JSON, email or PDF")
    digest = hashlib.sha256(content).hexdigest()
    with db.transaction(conn):
        operators.require_active(conn, session)
        # Content addresses are immutable; a second upload cannot replace the
        # original metadata, source identity or bytes.
        conn.execute(
            "INSERT OR IGNORE INTO evidence_file(sha256,filename,media_type,encrypted_content,"
            "size_bytes,uploaded_by,uploaded_at) VALUES(?,?,?,?,?,?,?)",
            (
                digest,
                filename,
                media_type,
                vault.encrypt_bytes(content),
                len(content),
                session.user_id,
                operators.utcnow().isoformat(),
            ),
        )
        audit.append(
            conn,
            "evidence.uploaded",
            {"sha256": digest, "size_bytes": len(content), "uploaded_by": session.user_id},
        )
    return {"sha256": digest, "size_bytes": len(content)}


def read(conn: db.Connection, vault: DetailVault, digest: str) -> tuple[db.sqlite3.Row, bytes]:
    row = require(conn, digest)
    content = vault.decrypt_bytes(row["encrypted_content"])
    if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != digest:
        raise EvidenceError("Source evidence integrity verification failed")
    return row, content


def bank_request_text(conn: db.Connection, vault: DetailVault, digest: str) -> str:
    row, content = read(conn, vault, digest)
    if row["media_type"] not in {"text/plain", "application/json", "message/rfc822"}:
        raise EvidenceError("Supply the original bank request as UTF-8 text, JSON or plain email")
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        raise EvidenceError("Bank request must contain valid UTF-8 text") from None
    # No attachment extraction or hidden HTML parsing is silently claimed here.
    # The caller supplies a readable source; PDFs remain usable for invoices.
    if row["media_type"] == "message/rfc822" and re.search(
        r"(?im)^content-type:\s*(?:multipart/|text/html)", text
    ):
        raise EvidenceError("Convert multipart or HTML email to readable UTF-8 text before intake")
    if row["media_type"] == "message/rfc822" and re.search(
        r"(?im)^content-transfer-encoding:\s*(?:base64|quoted-printable)", text
    ):
        raise EvidenceError("Decode encoded email to readable UTF-8 text before intake")
    return text
