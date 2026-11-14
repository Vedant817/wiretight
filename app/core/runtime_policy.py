"""Production policy trust: two real passkeys, no public HMAC fallback."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from yaml.tokens import AliasToken, AnchorToken

from app.core import db, record_signing
from app.core.policy import LoadedPolicy, PolicyError, _reject_unsafe_yaml
from app.core.policy_floor import check_policy_against_floor, validate_shape
from app.core.signing import Passkeys


def validated_policy(conn: db.Connection, path: str | Path) -> tuple[LoadedPolicy, dict[str, Any]]:
    target = Path(path)
    raw = target.read_bytes()
    try:
        if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(raw)):
            raise PolicyError("Policy aliases and anchors are forbidden")
    except yaml.YAMLError:
        raise PolicyError("Policy YAML is invalid") from None
    data = _reject_unsafe_yaml(raw.decode("utf-8"), target)
    if validate_shape(data) or not check_policy_against_floor(data).ok:
        raise PolicyError("Policy shape or safety floor is invalid")
    if data.get("demo_timing") or data["t0"]["enabled"]:
        raise PolicyError("Runtime requires full cooling and human approval for every money action")
    entity = conn.execute("SELECT id FROM entity").fetchall()
    if len(entity) != 1 or data["entity_id"] != entity[0]["id"] or data["base_currency"] != "USD":
        raise PolicyError("Policy entity/base currency does not match this installation")
    actual = [
        dict(row)
        for row in conn.execute(
            "SELECT u.id,u.name,u.role,u.email FROM user u JOIN operator_auth a ON a.user_id=u.id "
            "WHERE a.enabled=1 ORDER BY u.id",
        ).fetchall()
    ]
    if sorted(data["roster"], key=lambda item: item["id"]) != actual:
        raise PolicyError("Policy roster differs from enabled operators; update and re-sign policy")
    if sum(user["role"] == "approver" for user in actual) < 3 or not any(
        user["role"] == "ops" for user in actual
    ):
        raise PolicyError("Runtime requires three approvers and a separate ops operator")
    digest = hashlib.sha256(raw).hexdigest()
    decision = {"kind": "POLICY", "file_sha256": digest, "entity_id": data["entity_id"]}
    return LoadedPolicy(path=target, policy=data, sha256=digest), decision


def load_runtime_policy(conn: db.Connection, path: str | Path, passkeys: Passkeys) -> LoadedPolicy:
    policy, record = validated_policy(conn, path)
    record_signing.verify_records(
        conn, passkeys, purpose="POLICY", subject_id=policy.sha256, record=record, required=2
    )
    return policy
