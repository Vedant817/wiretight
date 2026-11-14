"""Passkey attestations for policy, callback and halt-clearing records.

These records never accept the historical public HMAC test signers. HTTP callers
must construct the subject from authoritative data before starting a ceremony.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from webauthn import (
    generate_authentication_options,
    options_to_json,
    verify_authentication_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement

from app.core import audit, db
from app.core.operators import Session, require_active, utcnow
from app.core.signing import Passkeys, SigningError
from app.money import raise_on_float

Purpose = Literal["POLICY", "CALLBACK", "CLEAR"]


def _role(purpose: Purpose) -> str:
    return "ops" if purpose == "CALLBACK" else "approver"


def _key_evidence(conn: db.Connection, user: db.sqlite3.Row) -> None:
    entry = conn.execute(
        "SELECT payload_json FROM audit_log WHERE kind='operator.passkey_registered' "
        "AND json_extract(payload_json,'$.user_id')=? ORDER BY seq ASC LIMIT 1",
        (user["id"],),
    ).fetchone()
    if not entry or not user["public_key"] or not user["webauthn_credential_id"]:
        raise SigningError("Audited passkey registration is missing")
    expected = json.loads(entry["payload_json"])
    if (
        expected.get("public_key_sha256") != hashlib.sha256(user["public_key"]).hexdigest()
        or expected.get("credential_id_sha256")
        != hashlib.sha256(base64url_to_bytes(user["webauthn_credential_id"])).hexdigest()
    ):
        raise SigningError("Passkey does not match audited registration")


def begin_record(
    conn: db.Connection,
    session: Session,
    passkeys: Passkeys,
    *,
    purpose: Purpose,
    subject_id: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    raise_on_float(record)
    canonical = audit.canonical_json(record)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    if not subject_id or len(subject_id) > 200:
        raise SigningError("Invalid signing subject")
    with db.transaction(conn):
        require_active(conn, session)
        if session.role != _role(purpose):
            raise SigningError("Operator role is not permitted for this decision")
        user = conn.execute("SELECT * FROM user WHERE id=?", (session.user_id,)).fetchone()
        _key_evidence(conn, user)
        if conn.execute(
            "SELECT 1 FROM signed_record WHERE purpose=? AND subject_id=? AND user_id=?",
            (purpose, subject_id, session.user_id),
        ).fetchone():
            raise SigningError("Operator already signed this decision")
        nonce = secrets.token_bytes(32)
        # Purpose and subject are domain-separated, preventing a callback or
        # policy signature from being replayed as a payment approval.
        challenge = hashlib.sha256(
            purpose.encode() + b"|" + subject_id.encode() + bytes.fromhex(digest) + nonce
        ).digest()
        options = generate_authentication_options(
            rp_id=passkeys.rp_id,
            challenge=challenge,
            timeout=300000,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(user["webauthn_credential_id"]))
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        ceremony_id = str(uuid4())
        now = utcnow()
        conn.execute(
            "DELETE FROM signing_challenge WHERE user_id=? AND consumed_at IS NULL",
            (session.user_id,),
        )
        conn.execute(
            "INSERT INTO signing_challenge(id,user_id,session_hash,purpose,subject_id,subject_hash,"
            "nonce,challenge,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                ceremony_id,
                session.user_id,
                session.token_hash,
                purpose,
                subject_id,
                digest,
                nonce.hex(),
                challenge,
                now.isoformat(),
                (now + timedelta(minutes=5)).isoformat(),
            ),
        )
        conn.execute(
            "UPDATE signing_challenge SET record_json=? WHERE id=?", (canonical, ceremony_id)
        )
        return {
            "ceremony_id": ceremony_id,
            "record": record,
            "sha256": digest,
            "publicKey": json.loads(options_to_json(options)),
        }


def finish_record(
    conn: db.Connection,
    session: Session,
    passkeys: Passkeys,
    *,
    purpose: Purpose,
    subject_id: str,
    record: dict[str, Any],
    ceremony_id: str,
    credential: dict[str, Any],
) -> str:
    raise_on_float(record)
    canonical = audit.canonical_json(record)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    with db.transaction(conn):
        require_active(conn, session)
        if session.role != _role(purpose):
            raise SigningError("Operator role is not permitted for this decision")
        ceremony = conn.execute(
            "SELECT * FROM signing_challenge WHERE id=?", (ceremony_id,)
        ).fetchone()
        if (
            not ceremony
            or ceremony["user_id"] != session.user_id
            or ceremony["session_hash"] != session.token_hash
            or ceremony["purpose"] != purpose
            or ceremony["subject_id"] != subject_id
            or ceremony["subject_hash"] != digest
            or ceremony["consumed_at"]
            or ceremony["expires_at"] <= utcnow().isoformat()
        ):
            raise SigningError("Decision changed, ceremony expired, or signature replayed")
        if conn.execute(
            "SELECT 1 FROM signed_record WHERE purpose=? AND subject_id=? AND user_id=?",
            (purpose, subject_id, session.user_id),
        ).fetchone():
            raise SigningError("Operator already signed this decision")
        user = conn.execute("SELECT * FROM user WHERE id=?", (session.user_id,)).fetchone()
        _key_evidence(conn, user)
        try:
            assertion = verify_authentication_response(
                credential=credential,
                expected_challenge=ceremony["challenge"],
                expected_rp_id=passkeys.rp_id,
                expected_origin=passkeys.origin,
                credential_public_key=user["public_key"],
                credential_current_sign_count=user["sign_count"],
                require_user_verification=True,
            )
            if credential.get("id") != user["webauthn_credential_id"]:
                raise SigningError("Credential belongs to a different operator")
        except (WebAuthnException, ValueError, KeyError, TypeError):
            raise SigningError("Decision passkey verification failed") from None
        material = {
            "credential": credential,
            "prior_sign_count": user["sign_count"],
            "rp_id": passkeys.rp_id,
            "origin": passkeys.origin,
            "ceremony_id": ceremony_id,
        }
        record_id = str(uuid4())
        now = utcnow().isoformat()
        conn.execute(
            "INSERT INTO signed_record(id,purpose,subject_id,canonical_json,sha256,user_id,"
            "assertion,nonce,signed_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                purpose,
                subject_id,
                canonical,
                digest,
                session.user_id,
                audit.canonical_json(material).encode(),
                ceremony["nonce"],
                now,
            ),
        )
        conn.execute(
            "UPDATE user SET sign_count=? WHERE id=?", (assertion.new_sign_count, session.user_id)
        )
        conn.execute("UPDATE signing_challenge SET consumed_at=? WHERE id=?", (now, ceremony_id))
        audit.append(
            conn,
            "decision.signed",
            {
                "record_id": record_id,
                "purpose": purpose,
                "subject_id": subject_id,
                "sha256": digest,
                "user_id": session.user_id,
            },
        )
        return record_id


def verify_records(
    conn: db.Connection,
    passkeys: Passkeys,
    *,
    purpose: Purpose,
    subject_id: str,
    record: dict[str, Any],
    required: int,
) -> list[str]:
    """Re-verify signatures and audited identity bindings, not a status column."""
    canonical = audit.canonical_json(record)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    rows = conn.execute(
        "SELECT * FROM signed_record WHERE purpose=? AND subject_id=?", (purpose, subject_id)
    ).fetchall()
    seen: set[str] = set()
    if required < 1:
        raise SigningError("A human decision requires signatures")
    for row in rows:
        if row["canonical_json"] != canonical or row["sha256"] != digest:
            raise SigningError("Stored decision terms changed")
        user = conn.execute(
            "SELECT u.*,a.enabled FROM user u JOIN operator_auth a ON a.user_id=u.id WHERE u.id=?",
            (row["user_id"],),
        ).fetchone()
        if not user or not user["enabled"] or user["role"] != _role(purpose) or user["id"] in seen:
            raise SigningError("Decision signer revoked, conflicted or duplicated")
        _key_evidence(conn, user)
        try:
            material = json.loads(row["assertion"])
            challenge = hashlib.sha256(
                purpose.encode()
                + b"|"
                + subject_id.encode()
                + bytes.fromhex(digest)
                + bytes.fromhex(row["nonce"])
            ).digest()
            if material["rp_id"] != passkeys.rp_id or material["origin"] != passkeys.origin:
                raise SigningError("Decision signing origin changed")
            verified = verify_authentication_response(
                credential=material["credential"],
                expected_challenge=challenge,
                expected_rp_id=passkeys.rp_id,
                expected_origin=passkeys.origin,
                credential_public_key=user["public_key"],
                credential_current_sign_count=material["prior_sign_count"],
                require_user_verification=True,
            )
            ceremony = conn.execute(
                "SELECT * FROM signing_challenge WHERE id=?", (material["ceremony_id"],)
            ).fetchone()
            if (
                not ceremony
                or not ceremony["consumed_at"]
                or ceremony["purpose"] != purpose
                or ceremony["subject_id"] != subject_id
                or ceremony["subject_hash"] != digest
                or ceremony["user_id"] != user["id"]
                or ceremony["challenge"] != challenge
                or ceremony["created_at"] > row["signed_at"]
                or ceremony["expires_at"] < row["signed_at"]
                or material["credential"]["id"] != user["webauthn_credential_id"]
                or user["sign_count"] < verified.new_sign_count
            ):
                raise SigningError("Decision ceremony evidence is invalid")
            if purpose == "CLEAR" and (
                not record.get("expires_at")
                or datetime.fromisoformat(record["expires_at"]) <= utcnow()
                or datetime.fromisoformat(record["expires_at"])
                > datetime.fromisoformat(record["created_at"]) + timedelta(hours=4)
                or datetime.fromisoformat(record["created_at"]) > utcnow() + timedelta(seconds=120)
            ):
                raise SigningError("Halt clearing approval expired")
        except (WebAuthnException, ValueError, KeyError, TypeError):
            raise SigningError("Stored decision signature failed verification") from None
        seen.add(user["id"])
    if len(seen) < required:
        raise SigningError("Insufficient independent decision signatures")
    return sorted(seen)
