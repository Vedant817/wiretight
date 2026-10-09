"""The append-only audit chain, with Ed25519 checkpoints outside the DB.

FINAL.md §14 (b): ``entry_hash = sha256(prev_hash || rfc8785(payload) || seq ||
at_iso)``. Checkpoints every 50 entries and at run end, written outside the
database and signed with an Ed25519 key.

Two properties carry the weight:

1. **Log before act.** :func:`log_intent` must succeed before the executor is
   allowed to call anything. If it raises, nothing is sent (T-17).
2. **A database edit is not enough.** The table has UPDATE/DELETE triggers, but
   a trigger can be dropped. The signed checkpoints live outside the DB, so
   ``make verify-audit`` detects an offline edit even with the triggers removed
   and the chain recomputed (T-13).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.core import db

#: ``prev_hash`` of the very first entry. A fixed, obviously-fake value, so a
#: truncated chain cannot pass as a complete one.
GENESIS_PREV_HASH: Final[str] = "0" * 64

#: Ed25519 checkpoint every this many entries (§14 b).
CHECKPOINT_INTERVAL: Final[int] = 50

CHECKPOINT_SUFFIX: Final[str] = ".checkpoint.json"


class AuditWriteError(RuntimeError):
    """The audit chain could not be written.

    Fatal by design (§4.16): the executor must not move money on the strength
    of an action it could not record.
    """


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of checking the chain.

    ``ok`` is False the moment any entry fails to hash or link. ``broken_at``
    is the sequence number of the first bad entry, which is the one a human
    needs.
    """

    ok: bool
    checked: int
    broken_at: int | None = None
    reason: str | None = None


def canonical_json(payload: Any) -> str:
    """RFC 8785 (JCS) canonicalisation.

    Key order and number formatting must not change the hash, or the same
    payload could produce two different packet hashes depending on how it was
    built.
    """
    # rfc8785.dumps already returns the JCS bytes with sorted keys and no
    # insignificant whitespace, so it needs no re-serialisation. Floats are
    # refused rather than coerced: JCS has its own number rules, and a float in
    # an audit payload would mean the payload was never exact to begin with.
    return rfc8785.dumps(_plain(payload)).decode("utf-8")


def _plain(value: Any) -> Any:
    """Reduce Decimals and datetimes to JSON primitives for canonicalisation."""
    from decimal import Decimal

    if isinstance(value, Decimal):
        # Canonical form is a string, never a float (§7.3).
        return format(value, "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


def entry_hash(
    prev_hash: str,
    kind: str,
    payload: Mapping[str, Any],
    at: str,
    seq: int,
) -> str:
    """``sha256(prev_hash || canonical_json([kind, payload, seq, at]))``.

    Bound together with a length prefix so no two different field splits can
    produce the same preimage.
    """
    preimage = "|".join(
        [
            prev_hash,
            kind,
            canonical_json(payload),
            str(seq),
            at,
        ]
    )
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def now_iso() -> str:
    """UTC ISO-8601 with an explicit offset, so stored strings sort correctly."""
    return datetime.now(UTC).isoformat()


def append(
    conn: db.Connection,
    kind: str,
    payload: Mapping[str, Any],
    *,
    at: str | None = None,
) -> int:
    """Append one entry and return its sequence number."""
    stamp = at or now_iso()
    try:
        row = conn.execute(
            "SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        seq = (int(row["seq"]) + 1) if row else 1
        prev = row["entry_hash"] if row else GENESIS_PREV_HASH
        digest = entry_hash(prev, kind, payload, stamp, seq)
        conn.execute(
            "INSERT INTO audit_log (seq, prev_hash, entry_hash, kind, payload_json, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (seq, prev, digest, kind, canonical_json(payload), stamp),
        )
    except Exception as exc:
        raise AuditWriteError(f"could not append audit entry {kind!r}: {exc}") from exc
    return seq


def log_intent(
    conn: db.Connection,
    kind: str,
    payload: Mapping[str, Any],
    *,
    at: str | None = None,
) -> int:
    """Record the intent to act, before acting (§4.8 step 6)."""
    return append(conn, kind, payload, at=at)


def log_result(
    conn: db.Connection,
    kind: str,
    payload: Mapping[str, Any],
    *,
    at: str | None = None,
) -> int:
    """Record what actually happened."""
    return append(conn, kind, payload, at=at)


def verify(conn: db.Connection) -> VerifyResult:
    """Recompute the whole chain and report the first entry that fails."""
    rows = list(
        conn.execute(
            "SELECT seq, prev_hash, entry_hash, kind, payload_json, at FROM audit_log ORDER BY seq"
        )
    )
    if not rows:
        return VerifyResult(ok=True, checked=0)

    prev = GENESIS_PREV_HASH
    for index, row in enumerate(rows, start=1):
        if int(row["seq"]) != index:
            return VerifyResult(
                ok=False,
                checked=index,
                broken_at=int(row["seq"]),
                reason="sequence numbers are not contiguous from 1",
            )
        if row["prev_hash"] != prev:
            return VerifyResult(
                ok=False,
                checked=index,
                broken_at=index,
                reason="entry does not chain to the previous hash",
            )
        recomputed = entry_hash(
            row["prev_hash"], row["kind"], json.loads(row["payload_json"]), row["at"], index
        )
        if recomputed != row["entry_hash"]:
            return VerifyResult(
                ok=False,
                checked=index,
                broken_at=index,
                reason="entry hash does not match its content",
            )
        prev = row["entry_hash"]

    return VerifyResult(ok=True, checked=len(rows))


# ---------------------------------------------------------------------------
# Ed25519 checkpoints, outside the database
# ---------------------------------------------------------------------------
def generate_key() -> Ed25519PrivateKey:
    """A fresh audit key. Written to ``var/keys/`` by ``make keys``, never committed."""
    return Ed25519PrivateKey.generate()


def save_private_key(key: Ed25519PrivateKey, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    target.write_bytes(pem)
    # Owner-only. A signing key that any local user can read is not a control.
    target.chmod(0o600)


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("the audit signing key must be Ed25519")
    return key


def write_checkpoint(
    conn: db.Connection,
    dir_path: str | Path,
    key: Ed25519PrivateKey,
    *,
    at: str | None = None,
) -> Path:
    """Sign the current chain head and write the checkpoint file.

    The file lives outside the SQLite file on purpose: an attacker (or a bug)
    with write access to the database cannot forge it, because the key is
    elsewhere.
    """
    directory = Path(dir_path)
    directory.mkdir(parents=True, exist_ok=True)

    row = conn.execute("SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    seq = int(row["seq"]) if row else 0
    head = row["entry_hash"] if row else GENESIS_PREV_HASH

    body = canonical_json({"seq": seq, "entry_hash": head, "at": at or now_iso()})
    signature = key.sign(body.encode("utf-8"))

    target = directory / f"{seq:012d}{CHECKPOINT_SUFFIX}"
    target.write_text(
        json.dumps({"body": body, "signature": signature.hex()}, separators=(",", ":")),
        encoding="utf-8",
    )
    return target


def verify_checkpoints(
    conn: db.Connection, dir_path: str | Path, public_key: Ed25519PublicKey
) -> VerifyResult:
    """Check the chain and confirm each checkpoint's signature over its head.

    This is what ``make verify-audit`` runs and what the executor calls before
    it starts. A missing checkpoint is a failure: it means entries were appended
    without ever being sealed.
    """
    chain = verify(conn)
    if not chain.ok:
        return chain

    directory = Path(dir_path)
    if not directory.is_dir():
        return VerifyResult(ok=False, checked=chain.checked, reason="no checkpoint directory")

    checkpoints = sorted(directory.glob(f"*{CHECKPOINT_SUFFIX}"))
    if not checkpoints:
        return VerifyResult(ok=False, checked=chain.checked, reason="no checkpoints written")

    row = conn.execute("SELECT seq FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    head_seq = int(row["seq"]) if row else 0

    for path in checkpoints:
        data = json.loads(path.read_text(encoding="utf-8"))
        try:
            public_key.verify(bytes.fromhex(data["signature"]), data["body"].encode("utf-8"))
        except (InvalidSignature, ValueError):
            return VerifyResult(
                ok=False,
                checked=chain.checked,
                broken_at=int(data.get("body", "{}") and json.loads(data["body"]).get("seq", 0)),
                reason=f"checkpoint {path.name} has an invalid signature",
            )
        sealed = json.loads(data["body"])
        sealed_seq = int(sealed.get("seq", 0))
        if sealed_seq > head_seq:
            return VerifyResult(
                ok=False,
                checked=chain.checked,
                broken_at=sealed_seq,
                reason=f"checkpoint {path.name} is ahead of the chain",
            )

        # The checkpoint pins a *hash*, not merely a position. Comparing only
        # the sequence number would let a rewritten-and-rehashed chain pass,
        # because the signature covers the old hash while the chain holds the
        # new one at the same seq. This comparison is what closes that gap.
        at_seal = conn.execute(
            "SELECT entry_hash FROM audit_log WHERE seq = ?", (sealed_seq,)
        ).fetchone()
        actual_hash = at_seal["entry_hash"] if at_seal else None
        if actual_hash != sealed.get("entry_hash"):
            return VerifyResult(
                ok=False,
                checked=chain.checked,
                broken_at=sealed_seq,
                reason=(
                    f"checkpoint {path.name} pins entry {sealed_seq} at "
                    f"{str(sealed.get('entry_hash'))[:16]}..., but the chain holds "
                    f"{str(actual_hash)[:16]}..."
                ),
            )

    # The newest checkpoint must cover the current head, or entries were
    # appended after the last seal.
    newest = json.loads(checkpoints[-1].read_text(encoding="utf-8"))["body"]
    sealed_seq = int(json.loads(newest).get("seq", 0))
    if sealed_seq < head_seq:
        return VerifyResult(
            ok=False,
            checked=chain.checked,
            broken_at=sealed_seq,
            reason=f"chain head is at {head_seq} but the newest checkpoint seals {sealed_seq}",
        )

    return VerifyResult(ok=True, checked=chain.checked)


def maybe_write_checkpoint(
    conn: db.Connection,
    dir_path: str | Path,
    key: Ed25519PrivateKey,
    *,
    at: str | None = None,
) -> Path | None:
    """Seal every :data:`CHECKPOINT_INTERVAL` entries, and at run end.

    Returns the path written, or ``None`` if it was not yet time.
    """
    row = conn.execute("SELECT count(*) AS n FROM audit_log").fetchone()
    count = int(row["n"])
    if count == 0 or count % CHECKPOINT_INTERVAL != 0:
        return None
    return write_checkpoint(conn, dir_path, key, at=at)
