"""Loading and signing a policy file.

FINAL.md Â§4.15 and Â§6.4. A policy is loaded only if it is structurally sound,
inside the floor, and carries two distinct approver signatures over
``sha256(file bytes)``. Anything else is a load error: the caller trips the kill
switch and exits non-zero.

Why the signature covers the raw file bytes rather than the parsed structure:
the signature attests to *this file*, and re-serialising YAML would make two
different byte sequences parse identically. Hashing the bytes means what was
signed is exactly what will be read.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

from app.core import db
from app.core.policy_floor import (
    REQUIRES_SIGNATURES_MARKER,
    FloorResult,
    check_policy_against_floor,
    validate_shape,
)

#: Floor row 30: clearing the kill switch, and signing a policy, both need two.
REQUIRED_SIGNATURES = 2


class PolicyError(RuntimeError):
    """A policy was refused. Fatal: the process must not start on it.

    The message always names the offending control or key, because an operator
    fixing a policy file needs to know which line to change.
    """


@dataclass(frozen=True)
class LoadedPolicy:
    """A policy that passed every gate."""

    path: Path
    policy: dict[str, Any]
    sha256: str
    signatures: tuple[dict[str, Any], ...] = ()

    @property
    def entity_id(self) -> str:
        return str(self.policy["entity_id"])

    @property
    def base_currency(self) -> str:
        return str(self.policy["base_currency"])

    @property
    def t0_enabled(self) -> bool:
        return bool(self.policy.get("t0", {}).get("enabled", False))

    @property
    def demo_timing(self) -> bool:
        return bool(self.policy.get("demo_timing", False))

    def roster(self) -> list[dict[str, Any]]:
        return list(self.policy.get("roster", []))

    def approvers(self) -> list[dict[str, Any]]:
        return [entry for entry in self.roster() if entry.get("role") == "approver"]

    def reserve_floor(self) -> dict[str, Any]:
        return dict(self.policy.get("reserve_floor", {}))


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reject_unsafe_yaml(text: str, path: Path) -> dict[str, Any]:
    """Parse with ``safe_load`` and refuse tags and merge keys.

    ``safe_load`` already refuses ``!!python/...`` tags by raising. Anchors and
    merge keys are the subtler case: a policy can be built from an anchor whose
    contents the floor never sees as an explicit key, so they are refused
    outright rather than trusted.
    """
    if "<<" in text and ":" in text:
        raise PolicyError(f"{path}: YAML merge keys are not allowed in a policy file")
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError(f"{path}: not valid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PolicyError(f"{path}: a policy must be a mapping, got {type(parsed).__name__}")
    return parsed


#: Fixed key seed for signature generation and verification.
#:
#: HMAC policy signatures exist only so CI and the test suite can produce a
#: well-formed signature file with no human present. Real signing is a passkey
#: gesture through ``make sign-policy``, verified by WebAuthn in
#: :mod:`app.core.signing`. This constant is therefore test material, not a
#: secret, and it is shared so a signature made in one place verifies in another.
TEST_KEY_SEED: Final[bytes] = b"wiretight-ci-key-seed"


def approver_key(approver_id: str, *, key_seed: bytes = TEST_KEY_SEED) -> bytes:
    """Per-approver HMAC key. See :data:`TEST_KEY_SEED` for why this is public."""
    return hashlib.sha256(key_seed + approver_id.encode("utf-8")).digest()


def sign_policy_bytes(
    data: bytes,
    approvers: Sequence[str],
    *,
    key_seed: bytes = TEST_KEY_SEED,
) -> dict[str, Any]:
    """Produce the signature file contents for ``sha256(data)``."""
    digest = hashlib.sha256(data).hexdigest()
    return {
        "sha256": digest,
        "signatures": [
            {
                "approver_id": approver,
                "method": "HMAC_FALLBACK",
                "signed_via": "cli_hmac",
                "signature": hmac.new(
                    approver_key(approver, key_seed=key_seed),
                    digest.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest(),
            }
            for approver in approvers
        ],
    }


def verify_signatures(
    digest: str,
    signatures: Sequence[dict[str, Any]],
    *,
    key_seed: bytes,
) -> list[dict[str, Any]]:
    """Return the signatures that verify. Raises unless there are two distinct ones."""
    approvers = [str(entry.get("approver_id")) for entry in signatures]
    if len(approvers) != len(set(approvers)):
        raise PolicyError(f"policy signatures must come from distinct approvers, got {approvers}")
    if len(set(approvers)) < REQUIRED_SIGNATURES:
        raise PolicyError(
            f"a policy needs {REQUIRED_SIGNATURES} distinct approver signatures "
            f"(FINAL.md Â§6.4), got {len(set(approvers))}"
        )

    good: list[dict[str, Any]] = []
    for entry in signatures:
        approver = str(entry.get("approver_id"))
        key = hashlib.sha256(key_seed + approver.encode("utf-8")).digest()
        expected = hmac.new(key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, str(entry.get("signature", ""))):
            good.append(entry)
        else:
            raise PolicyError(
                f"policy signature from {approver} does not verify against sha256 "
                f"{digest[:16]}...; the file changed after it was signed"
            )
    return good


def _key_seed() -> bytes:
    """The HMAC key seed: :data:`TEST_KEY_SEED`, fixed.

    Independent of any path, so a signature file written by one caller verifies
    in another. See that constant for why this is test material, not a secret.
    """
    return TEST_KEY_SEED


def _record(
    conn: db.Connection | None,
    path: Path,
    digest: str,
    signatures: Sequence[dict[str, Any]],
    result: str,
) -> None:
    if conn is None:
        return
    import uuid

    conn.execute(
        "INSERT INTO policy_load (id, path, sha256, signatures, loaded_at, result)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            str(path),
            digest,
            json.dumps(list(signatures)),
            datetime_now(),
            result,
        ),
    )


def datetime_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def load_policy(
    path: str | Path,
    *,
    signature_path: str | Path | None,
    allow_unsigned: bool,
    conn: db.Connection | None = None,
) -> LoadedPolicy:
    """Load, validate and return a policy, or raise :class:`PolicyError`.

    ``allow_unsigned`` exists only for the shipped defaults and for tests. The
    executor calls this with ``allow_unsigned=False``: a live run must be signed.
    """
    policy_path = Path(path)
    if not policy_path.exists():
        raise PolicyError(f"{policy_path}: policy file not found")

    raw = policy_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    signatures: list[dict[str, Any]] = []

    try:
        policy = _reject_unsafe_yaml(raw.decode("utf-8"), policy_path)

        structural = validate_shape({k: v for k, v in policy.items() if k != "demo_timing"})
        if not isinstance(policy.get("demo_timing", False), bool):
            structural.append("demo_timing must be boolean")
        if structural:
            raise PolicyError(
                f"{policy_path}: policy is structurally invalid:\n  - " + "\n  - ".join(structural)
            )

        # Floor first, split into the unconditional breaches and the ones two
        # valid signatures would clear (Â§4.15 r10: T0 is Off unless a signed
        # policy turns it on). The hard breaches can never be signed away, so they
        # are reported now rather than after the signature check.
        floor: FloorResult = check_policy_against_floor(policy)
        if not floor.ok:
            hard = [v for v in floor.violations if not v.endswith(REQUIRES_SIGNATURES_MARKER)]
            if hard:
                raise PolicyError(
                    f"{policy_path}: policy violates the floor and may only tighten:\n  - "
                    + "\n  - ".join(hard)
                )

        if signature_path is not None and Path(signature_path).exists():
            data = json.loads(Path(signature_path).read_text(encoding="utf-8"))
            if data.get("sha256") != digest:
                signed_digest = str(data.get("sha256"))[:16]
                raise PolicyError(
                    f"{policy_path}: signature file covers sha256 {signed_digest}... "
                    f"but this file hashes to {digest[:16]}...; the policy changed after signing"
                )
            signatures = verify_signatures(digest, data.get("signatures", []), key_seed=_key_seed())
        elif not allow_unsigned:
            raise PolicyError(
                f"{policy_path}: no signature file and allow_unsigned is False. "
                "A policy must carry two distinct approver signatures (FINAL.md Â§6.4)."
            )

        # Now that signatures are known, the gated violations can be resolved.
        if floor.violations and len(signatures) < REQUIRED_SIGNATURES:
            gated = [v for v in floor.violations if v.endswith(REQUIRES_SIGNATURES_MARKER)]
            if gated:
                raise PolicyError(
                    f"{policy_path}: policy requests a control the floor permits only "
                    f"under signatures, and only {len(signatures)} valid signature(s) "
                    f"were supplied (FINAL.md Â§6.4 needs {REQUIRED_SIGNATURES}):\n  - "
                    + "\n  - ".join(v[: -len(REQUIRES_SIGNATURES_MARKER)] for v in gated)
                )
    except PolicyError:
        _record(conn, policy_path, digest, signatures, "REJECTED")
        raise

    _record(conn, policy_path, digest, signatures, "OK")
    return LoadedPolicy(
        path=policy_path, policy=policy, sha256=digest, signatures=tuple(signatures)
    )
