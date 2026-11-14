"""Human passkey ceremonies bound to exact immutable approval packet hashes."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from sqlite3 import Row
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    UserVerificationRequirement,
)

from app.core import audit, db
from app.core.operators import Session, require_active, utcnow
from app.money import raise_on_float


class SigningError(RuntimeError):
    pass


def packet(conn: db.Connection, packet_id: str) -> Row:
    row: Row | None = conn.execute(
        "SELECT * FROM approval_packet WHERE id=?", (packet_id,)
    ).fetchone()
    if not row:
        raise SigningError("Approval packet not found")
    encoded = row["canonical_json"]
    if hashlib.sha256(encoded.encode()).hexdigest() != row["sha256"]:
        raise SigningError("Approval packet hash mismatch")
    payload = json.loads(encoded)
    raise_on_float(payload)
    if audit.canonical_json(payload) != encoded:
        raise SigningError("Approval packet is not canonical")
    if row["expires_at"] <= utcnow().isoformat() or row["state"] not in {"OPEN", "APPROVED"}:
        raise SigningError("Approval packet expired or unavailable")
    if row["required_approvers"] not in {1, 2} or row["tier"] == "T0":
        raise SigningError("Every money action needs human approval")
    if row["tier"] == "T2" and row["required_approvers"] != 2:
        raise SigningError("T2 requires two independent approvers")
    return row


def _eligible(
    conn: db.Connection, session: Session, row: Row, *, duplicate_check: bool = True
) -> None:
    if session.role != "approver":
        raise SigningError("Only approvers may sign payment or conversion packets")
    payload = json.loads(row["canonical_json"])
    if (
        payload.get("required_approvers") != row["required_approvers"]
        or payload.get("tier") != row["tier"]
        or payload.get("kind") != row["kind"]
    ):
        raise SigningError("Packet approval terms disagree with stored metadata")
    if row["tier"] == "T2":
        count = conn.execute(
            "SELECT COUNT(*) FROM user u JOIN operator_auth a ON a.user_id=u.id "
            "WHERE u.role='approver' AND a.enabled=1",
        ).fetchone()[0]
        if count < 3:
            raise SigningError("T2 requires a roster of at least three approvers")
    if payload.get("kind") == "PAYMENT":
        ids = [item["obligation_id"] for item in payload.get("items", [])]
    elif payload.get("kind") == "CONVERSION":
        ids = [item.rsplit(":", 1)[0] for item in payload.get("funded_items", [])]
    else:
        raise SigningError("Unknown packet kind")
    if not ids:
        raise SigningError("Packet has no obligations")
    for obligation_id in ids:
        obligation = conn.execute(
            "SELECT requester_set FROM obligation WHERE id=?", (obligation_id,)
        ).fetchone()
        if not obligation or session.user_id in json.loads(obligation["requester_set"]):
            raise SigningError("Requester cannot approve their own obligation")
    if (
        duplicate_check
        and conn.execute(
            "SELECT 1 FROM approval_signature WHERE packet_id=? AND approver_id=?",
            (row["id"], session.user_id),
        ).fetchone()
    ):
        raise SigningError("This approver already signed the packet")


class Passkeys:
    def __init__(self, *, rp_id: str, origin: str) -> None:
        parsed = urlsplit(origin)
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.scheme not in {"http", "https"}
            or not (parsed.hostname == rp_id or parsed.hostname.endswith("." + rp_id))
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"})
        ):
            raise ValueError("WebAuthn origin must be HTTPS (or localhost) and match RP ID")
        self.rp_id = rp_id
        self.origin = origin

    def begin(
        self, conn: db.Connection, session: Session, *, packet_id: str | None = None
    ) -> dict[str, Any]:
        with db.transaction(conn):
            require_active(conn, session)
            user = conn.execute("SELECT * FROM user WHERE id=?", (session.user_id,)).fetchone()
            if not user:
                raise SigningError("Unknown operator")
            nonce = secrets.token_bytes(32)
            subject_hash = None
            purpose = "REGISTER"
            options: PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions
            if packet_id:
                row = packet(conn, packet_id)
                _eligible(conn, session, row)
                if not user["public_key"]:
                    raise SigningError("Register a passkey before approving")
                subject_hash = row["sha256"]
                challenge = hashlib.sha256(bytes.fromhex(subject_hash) + nonce).digest()
                purpose = "APPROVE"
                options = generate_authentication_options(
                    rp_id=self.rp_id,
                    challenge=challenge,
                    timeout=300000,
                    allow_credentials=[
                        PublicKeyCredentialDescriptor(
                            id=base64url_to_bytes(user["webauthn_credential_id"])
                        )
                    ],
                    user_verification=UserVerificationRequirement.REQUIRED,
                )
            else:
                if user["public_key"]:
                    raise SigningError(
                        "Passkey already registered; reset requires local administration"
                    )
                challenge = nonce
                options = generate_registration_options(
                    rp_id=self.rp_id,
                    rp_name="Wiretight",
                    user_name=user["email"],
                    user_id=user["id"].encode(),
                    user_display_name=user["name"],
                    challenge=challenge,
                    timeout=300000,
                    authenticator_selection=AuthenticatorSelectionCriteria(
                        user_verification=UserVerificationRequirement.REQUIRED
                    ),
                )
            challenge_id = str(uuid4())
            now = utcnow()
            # One outstanding ceremony per identity avoids unlimited stale prompts.
            conn.execute(
                "DELETE FROM signing_challenge WHERE user_id=? AND consumed_at IS NULL",
                (session.user_id,),
            )
            conn.execute(
                "INSERT INTO signing_challenge(id,user_id,session_hash,purpose,subject_id,"
                "subject_hash,"
                "nonce,challenge,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    challenge_id,
                    session.user_id,
                    session.token_hash,
                    purpose,
                    packet_id,
                    subject_hash,
                    nonce.hex(),
                    challenge,
                    now.isoformat(),
                    (now + timedelta(minutes=5)).isoformat(),
                ),
            )
            return {"ceremony_id": challenge_id, "publicKey": json.loads(options_to_json(options))}

    def finish(
        self, conn: db.Connection, session: Session, *, ceremony_id: str, credential: dict[str, Any]
    ) -> None:
        with db.transaction(conn):
            require_active(conn, session)
            ceremony = conn.execute(
                "SELECT * FROM signing_challenge WHERE id=? AND user_id=? AND session_hash=?",
                (ceremony_id, session.user_id, session.token_hash),
            ).fetchone()
            if (
                not ceremony
                or ceremony["consumed_at"]
                or ceremony["expires_at"] <= utcnow().isoformat()
            ):
                raise SigningError("Passkey ceremony expired or already used")
            user = conn.execute("SELECT * FROM user WHERE id=?", (session.user_id,)).fetchone()
            if not user:
                raise SigningError("Unknown operator")
            try:
                if ceremony["purpose"] == "REGISTER":
                    if user["public_key"]:
                        raise SigningError("Passkey already registered")
                    verified = verify_registration_response(
                        credential=credential,
                        expected_challenge=ceremony["challenge"],
                        expected_rp_id=self.rp_id,
                        expected_origin=self.origin,
                        require_user_verification=True,
                    )
                    from webauthn.helpers.bytes_to_base64url import bytes_to_base64url

                    conn.execute(
                        "UPDATE user SET webauthn_credential_id=?,public_key=?,sign_count=? "
                        "WHERE id=?",
                        (
                            bytes_to_base64url(verified.credential_id),
                            verified.credential_public_key,
                            verified.sign_count,
                            session.user_id,
                        ),
                    )
                    audit.append(
                        conn,
                        "operator.passkey_registered",
                        {
                            "user_id": session.user_id,
                            "public_key_sha256": hashlib.sha256(
                                verified.credential_public_key
                            ).hexdigest(),
                            "credential_id_sha256": hashlib.sha256(
                                verified.credential_id
                            ).hexdigest(),
                        },
                    )
                elif ceremony["purpose"] == "APPROVE":
                    row = packet(conn, ceremony["subject_id"])
                    _eligible(conn, session, row)
                    if row["sha256"] != ceremony["subject_hash"]:
                        raise SigningError("Packet changed during sign-off")
                    assertion = verify_authentication_response(
                        credential=credential,
                        expected_challenge=ceremony["challenge"],
                        expected_rp_id=self.rp_id,
                        expected_origin=self.origin,
                        credential_public_key=user["public_key"],
                        credential_current_sign_count=user["sign_count"],
                        require_user_verification=True,
                    )
                    if credential.get("id") != user["webauthn_credential_id"]:
                        raise SigningError("Credential belongs to a different operator")
                    material = {
                        "credential": credential,
                        "prior_sign_count": user["sign_count"],
                        "rp_id": self.rp_id,
                        "origin": self.origin,
                        "ceremony_id": ceremony_id,
                    }
                    now = utcnow()
                    conn.execute(
                        "INSERT INTO approval_signature(id,packet_id,approver_id,method,signed_via,"
                        "assertion,challenge_nonce,signed_at) "
                        "VALUES(?,?,?,'WEBAUTHN','ui_passkey',?,?,?)",
                        (
                            str(uuid4()),
                            row["id"],
                            session.user_id,
                            audit.canonical_json(material).encode(),
                            ceremony["nonce"],
                            now.isoformat(),
                        ),
                    )
                    conn.execute(
                        "UPDATE user SET sign_count=? WHERE id=?",
                        (assertion.new_sign_count, session.user_id),
                    )
                    count = conn.execute(
                        "SELECT COUNT(*) FROM approval_signature WHERE packet_id=?", (row["id"],)
                    ).fetchone()[0]
                    state = "APPROVED" if count >= row["required_approvers"] else "OPEN"
                    first = conn.execute(
                        "SELECT MIN(signed_at) FROM approval_signature WHERE packet_id=?",
                        (row["id"],),
                    ).fetchone()[0]
                    # Expiry cannot be extended by a later sign-off.
                    expires = min(
                        row["expires_at"],
                        (datetime.fromisoformat(first) + timedelta(hours=4)).isoformat(),
                    )
                    conn.execute(
                        "UPDATE approval_packet SET state=?,expires_at=? WHERE id=?",
                        (state, expires, row["id"]),
                    )
                    audit.append(
                        conn,
                        "approval.signed",
                        {
                            "packet_id": row["id"],
                            "user_id": session.user_id,
                            "packet_sha256": row["sha256"],
                        },
                    )
                else:
                    raise SigningError("Unsupported passkey ceremony")
            except (WebAuthnException, ValueError, KeyError, TypeError):
                raise SigningError("Passkey verification failed") from None
            conn.execute(
                "UPDATE signing_challenge SET consumed_at=? WHERE id=?",
                (utcnow().isoformat(), ceremony_id),
            )

    def verify_stored(self, conn: db.Connection, packet_id: str) -> None:
        """Executor checks actual stored assertions; APPROVED is never evidence."""
        row = packet(conn, packet_id)
        signatures = conn.execute(
            "SELECT * FROM approval_signature WHERE packet_id=?", (packet_id,)
        ).fetchall()
        if len(signatures) < row["required_approvers"]:
            raise SigningError("Insufficient human approvals")
        seen = set()
        for signature in signatures:
            if datetime.fromisoformat(signature["signed_at"]) + timedelta(hours=4) <= utcnow():
                raise SigningError("Human approval expired")
            user = conn.execute(
                "SELECT u.*,a.enabled FROM user u JOIN operator_auth a ON a.user_id=u.id "
                "WHERE u.id=?",
                (signature["approver_id"],),
            ).fetchone()
            if not user or not user["enabled"] or user["role"] != "approver" or user["id"] in seen:
                raise SigningError("Approval signer revoked or duplicated")
            if signature["method"] != "WEBAUTHN" or signature["signed_via"] != "ui_passkey":
                raise SigningError("Only verified human passkey approvals are supported")
            seen.add(user["id"])
            registration = conn.execute(
                "SELECT payload_json FROM audit_log WHERE kind='operator.passkey_registered' "
                "AND json_extract(payload_json,'$.user_id')=? ORDER BY seq ASC LIMIT 1",
                (user["id"],),
            ).fetchone()
            if not registration:
                raise SigningError("Audited passkey registration is missing")
            recorded = json.loads(registration["payload_json"])
            if (
                recorded.get("public_key_sha256") != hashlib.sha256(user["public_key"]).hexdigest()
                or recorded.get("credential_id_sha256")
                != hashlib.sha256(base64url_to_bytes(user["webauthn_credential_id"])).hexdigest()
            ):
                raise SigningError("Passkey no longer matches audited registration")
            _eligible(
                conn,
                Session(user["id"], user["name"], user["role"], ""),
                row,
                duplicate_check=False,
            )
            try:
                material = json.loads(signature["assertion"])
                nonce = bytes.fromhex(signature["challenge_nonce"])
                challenge = hashlib.sha256(bytes.fromhex(row["sha256"]) + nonce).digest()
                if material["origin"] != self.origin or material["rp_id"] != self.rp_id:
                    raise SigningError("Signing origin configuration changed")
                verified = verify_authentication_response(
                    credential=material["credential"],
                    expected_challenge=challenge,
                    expected_rp_id=self.rp_id,
                    expected_origin=self.origin,
                    credential_public_key=user["public_key"],
                    credential_current_sign_count=material["prior_sign_count"],
                    require_user_verification=True,
                )
                if (
                    material["credential"]["id"] != user["webauthn_credential_id"]
                    or user["sign_count"] < verified.new_sign_count
                ):
                    raise SigningError("Stored credential or counter mismatch")
                ceremony = conn.execute(
                    "SELECT * FROM signing_challenge WHERE id=?", (material["ceremony_id"],)
                ).fetchone()
                if (
                    not ceremony
                    or not ceremony["consumed_at"]
                    or ceremony["user_id"] != user["id"]
                    or ceremony["subject_hash"] != row["sha256"]
                    or ceremony["subject_id"] != packet_id
                    or ceremony["purpose"] != "APPROVE"
                    or ceremony["nonce"] != signature["challenge_nonce"]
                    or ceremony["challenge"] != challenge
                    or ceremony["created_at"] > signature["signed_at"]
                    or ceremony["expires_at"] < signature["signed_at"]
                ):
                    raise SigningError("Approval ceremony evidence missing")
            except (WebAuthnException, ValueError, KeyError, TypeError):
                raise SigningError("Stored approval signature failed verification") from None
