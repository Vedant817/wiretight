"""Administrator-pinned roster outside SQLite; worker seals cannot enroll keys."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from webauthn.helpers import base64url_to_bytes

from app.core import audit, db


def roster_material(conn: db.Connection) -> dict[str, Any]:
    material = {}
    for row in conn.execute(
        "SELECT u.* FROM user u JOIN operator_auth a ON a.user_id=u.id "
        "WHERE a.enabled=1 ORDER BY u.id"
    ):
        if not row["public_key"] or not row["webauthn_credential_id"]:
            raise ValueError(
                "Every enabled operator must register a passkey before roster trust is pinned"
            )
        material[row["id"]] = {
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "key_sha256": hashlib.sha256(row["public_key"]).hexdigest(),
            "credential_sha256": hashlib.sha256(
                base64url_to_bytes(row["webauthn_credential_id"])
            ).hexdigest(),
        }
    if not material:
        raise ValueError("No registered operators")
    return material


def pin_roster(conn: db.Connection, *, key_dir: Path, seal_dir: Path) -> None:
    key = audit.load_private_key(key_dir / "audit_ed25519.pem")
    public = Ed25519PublicKey.from_public_bytes((key_dir / "audit.public").read_bytes())
    if not audit.verify_checkpoints(conn, seal_dir, public).ok:
        raise ValueError("Audit verification failed; refusing to bless edited history")
    body = audit.canonical_json({"operators": roster_material(conn)})
    audit._write_durable(
        key_dir / "roster.trust.json",
        json.dumps({"body": body, "signature": key.sign(body.encode()).hex()}),
    )
    audit.write_checkpoint(conn, seal_dir, key, reason="operator-trust")


def verify_roster(conn: db.Connection, key_dir: Path, public: Ed25519PublicKey) -> None:
    try:
        envelope = json.loads((key_dir / "roster.trust.json").read_text(encoding="utf-8"))
        public.verify(bytes.fromhex(envelope["signature"]), envelope["body"].encode())
        if json.loads(envelope["body"])["operators"] != roster_material(conn):
            raise ValueError("Operator roster changed; local administrator must review and pin it")
    except (KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("Operator trust file is invalid") from None
