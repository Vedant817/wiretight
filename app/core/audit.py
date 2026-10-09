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
import os
import sqlite3
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
    """Append one entry and return its sequence number.

    The read-last-seq-then-insert is done inside ``BEGIN IMMEDIATE``, which takes
    SQLite's single write lock up front. Without it, two web threads appending
    concurrently both read the same head and the loser hit
    ``UNIQUE constraint failed: audit_log.seq`` — measured on 100% of concurrent
    appends. The write lock is held for one row insert and released immediately;
    it never spans a commit boundary or an API call.
    """
    stamp = at or now_iso()

    def attempt() -> int:
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
        return seq

    try:
        with db.transaction(conn):
            return attempt()
    except db.DatabaseBusyError:
        # Fail closed and loud. A dropped audit entry is a lost record of intent to
        # move money, so this must never be swallowed as "just retry later".
        raise AuditWriteError(
            f"could not append audit entry {kind!r}: the write lock could not be "
            "acquired. The executor must halt rather than act without a record "
            "(FINAL.md §4.16, §14 b)"
        ) from None
    except sqlite3.IntegrityError as exc:
        raise AuditWriteError(
            f"could not append audit entry {kind!r}: {exc}. A UNIQUE violation on "
            "audit_log.seq means two writers raced the chain head, which the "
            "BEGIN IMMEDIATE in append() is meant to prevent."
        ) from exc
    except sqlite3.Error as exc:
        raise AuditWriteError(f"could not append audit entry {kind!r}: {exc}") from exc


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
    reason: str = "interval",
) -> Path:
    """Sign the current chain head and write a checkpoint file.

    The file lives outside the SQLite file on purpose: an attacker (or a bug)
    with write access to the database cannot forge it, because the key is
    elsewhere.

    The filename carries the seq **and** a reason discriminator. Naming files
    ``{seq}.checkpoint.json`` meant a run-end seal silently overwrote the
    interval seal whenever the chain length was already a multiple of 50, so the
    number of seal files was not evidence of anything.
    """
    directory = Path(dir_path)
    directory.mkdir(parents=True, exist_ok=True)

    row = conn.execute("SELECT seq, entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    seq = int(row["seq"]) if row else 0
    head = row["entry_hash"] if row else GENESIS_PREV_HASH

    body = canonical_json({"seq": seq, "entry_hash": head, "at": at or now_iso(), "reason": reason})
    signature = key.sign(body.encode("utf-8"))

    target = directory / f"{seq:012d}.{reason}{CHECKPOINT_SUFFIX}"
    _write_durable(
        target,
        json.dumps({"body": body, "signature": signature.hex()}, separators=(",", ":")),
    )
    _advance_anchor(directory, seq, key, at=at)
    return target


#: The monotone head record. Its only job is to make tail truncation detectable.
#:
#: Every checkpoint file can be deleted along with the entries it covers, and the
#: surviving seals still verify: a seal at seq 100 pins entry 100's hash, and a
#: chain truncated to 100 has that same hash. So the highest seq ever sealed is
#: recorded in its own signed file, and truncation leaves the anchor pointing
#: past the end of the chain.
ANCHOR_NAME: Final[str] = "head.anchor.json"


def _write_durable(path: Path, text: str) -> None:
    """Write a file so that a crash leaves either the old content or the new.

    ``Path.write_text`` is open-write-close. A power loss between the write and
    the flush leaves a **truncated** file, and for the anchor that is
    indistinguishable from tampering: measured, truncating it made
    ``verify_checkpoints`` report the chain as unverified, which halts the
    executor (D-B21).

    The sequence is the only one that is crash-safe: write a temporary file in the
    same directory, ``fsync`` the data, ``os.replace`` (atomic on POSIX and on
    Windows for same-volume renames), then ``fsync`` the directory so the rename
    itself is durable.
    """
    tmp = path.with_name(f"{path.name}.tmp")
    fd = os.open(str(tmp), os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)

    tmp.replace(path)

    # fsync the directory so the rename survives. Windows has no directory fd
    # for this, which is why the guard is silent rather than fatal there.
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:  # pragma: no cover - not supported on this platform
        return
    try:
        os.fsync(dir_fd)
    except OSError:  # pragma: no cover - not supported on this platform
        pass
    finally:
        os.close(dir_fd)


def _advance_anchor(
    directory: Path, seq: int, key: Ed25519PrivateKey, *, at: str | None = None
) -> None:
    """Record the highest seq ever sealed. Only ever moves forward.

    Read-take-max-write, so replaying an older checkpoint cannot roll it back.

    **A corrupt anchor no longer resets the recorded maximum downward.** The
    ``except`` branch used to set ``highest = seq``, which is precisely the roll
    back the docstring claims cannot happen: with a 200-entry chain truncated to
    150, the corrupt anchor made the system believe 150 was the highest seq ever
    reached, and every truncation check passed (D-B21). The fallback is now the
    *current* value only when there is nothing to preserve; a damaged anchor
    raises so the failure is a halt, not a silently lowered bound.
    """
    anchor = directory / ANCHOR_NAME
    highest = seq
    if anchor.exists():
        try:
            previous = json.loads(anchor.read_text(encoding="utf-8"))
            highest = max(seq, int(json.loads(previous["body"])["seq"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise AnchorCorruptError(
                f"{anchor} exists but cannot be read ({exc}). Refusing to overwrite "
                "it: the anchor is the only record of how far this chain ever "
                "reached, so replacing it would erase the evidence of any "
                "truncation. Move it aside deliberately if this is expected."
            ) from exc

    body = canonical_json({"seq": highest, "at": at or now_iso()})
    _write_durable(
        anchor,
        json.dumps(
            {"body": body, "signature": key.sign(body.encode()).hex()},
            separators=(",", ":"),
        ),
    )


class AnchorCorruptError(RuntimeError):
    """The head anchor exists but cannot be read.

    Deliberately fatal rather than recoverable. The anchor is the one artefact
    that survives an attacker deleting every seal, so "rebuild it from what is
    left" is exactly the wrong move.
    """


def read_anchor(dir_path: str | Path, *, key: Ed25519PublicKey | None = None) -> int | None:
    """The highest seq the anchor claims was ever sealed, or ``None``.

    When ``key`` is supplied, the signature is **verified**. It used to be read
    and discarded, so the anchor was the one signed file in the system whose
    signature nothing checked: an attacker could rewrite the chain head to any
    value, delete the seals above it, and every verification path reported a
    clean, self-consistent, truncated chain (D-B21). Verifying is what makes this
    file load-bearing instead of decorative.
    """
    anchor = Path(dir_path) / ANCHOR_NAME
    if not anchor.exists():
        return None
    try:
        data = json.loads(anchor.read_text(encoding="utf-8"))
        body_text = data["body"]
        signature_hex = data["signature"]
        seq = int(json.loads(body_text)["seq"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

    if key is not None:
        try:
            key.verify(bytes.fromhex(signature_hex), body_text.encode("utf-8"))
        except (InvalidSignature, ValueError) as exc:
            raise AnchorCorruptError(
                f"{anchor}: signature does not verify against the body. The recorded "
                "chain head has been altered."
            ) from exc
    return seq


def _checkpoint_seq(data: dict[str, Any]) -> int:
    """The seq a checkpoint claims, tolerating a malformed file.

    A corrupt checkpoint must produce a *verification failure*, never a
    traceback: this runs before the executor starts, and a crash here would look
    like "verification did not run" rather than "verification failed".
    """
    try:
        return int(json.loads(data["body"])["seq"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return -1


def verify_checkpoints(
    conn: db.Connection, dir_path: str | Path, public_key: Ed25519PublicKey
) -> VerifyResult:
    """Check the chain, every checkpoint's signature, and the monotone anchor.

    This is what ``make verify-audit`` runs and what the executor calls before it
    starts. Three independent things must hold:

    1. the chain hashes and links correctly (``verify``);
    2. every checkpoint's signature is valid **and** the hash it pins matches the
       chain at that seq;
    3. the anchor's highest-ever-sealed seq does not exceed the chain head, and
       a seal exists at or past the head.

    (3) is what catches tail truncation. Without it, deleting entries and their
    matching seals leaves a self-consistent chain that verifies.
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

    # The anchor first: it is the check that survives deleting seal files. Its
    # signature is verified with the same public key as every seal, because an
    # unverified anchor is just a number someone can edit (D-B21).
    anchor_seq: int | None
    try:
        anchor_seq = read_anchor(directory, key=public_key)
    except AnchorCorruptError as exc:
        return VerifyResult(ok=False, checked=chain.checked, reason=str(exc))
    if anchor_seq is None:
        return VerifyResult(
            ok=False,
            checked=chain.checked,
            reason="no head anchor: the highest seq ever sealed is unknown",
        )
    if anchor_seq > head_seq:
        return VerifyResult(
            ok=False,
            checked=chain.checked,
            broken_at=anchor_seq,
            reason=(
                f"the head anchor records seq {anchor_seq} as sealed, but the chain "
                f"ends at {head_seq}: {anchor_seq - head_seq} entries and their seals "
                "were removed (FINAL.md §14 b, T-13)"
            ),
        )

    for path in checkpoints:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            body_text = data["body"]
            signature_hex = data["signature"]
            sealed = json.loads(body_text)
        except (json.JSONDecodeError, KeyError, TypeError):
            return VerifyResult(
                ok=False,
                checked=chain.checked,
                broken_at=-1,
                reason=f"checkpoint {path.name} is malformed",
            )

        try:
            public_key.verify(bytes.fromhex(signature_hex), body_text.encode("utf-8"))
        except (InvalidSignature, ValueError):
            return VerifyResult(
                ok=False,
                checked=chain.checked,
                broken_at=_checkpoint_seq(data),
                reason=f"checkpoint {path.name} has an invalid signature",
            )

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

    return VerifyResult(ok=True, checked=chain.checked)


def head_is_sealed(conn: db.Connection, dir_path: str | Path) -> VerifyResult:
    """Is the current chain head covered by a seal?

    Deliberately separate from :func:`verify_checkpoints`. An unsealed tail is a
    normal *mid-run* state — entries 101..110 exist, the next interval seal lands
    at 150 — so folding "the newest seal must cover the head" into the integrity
    check reported a false failure every few runs.

    Integrity asks "is this history what it claims to be". This asks "was the
    last run finished and sealed", and it is what the executor calls before it
    starts, because resuming a run from an unsealed chain is precisely what
    T-15's crash recovery relies on.
    """
    chain = verify(conn)
    if not chain.ok:
        return chain

    directory = Path(dir_path)
    row = conn.execute("SELECT seq FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    head_seq = int(row["seq"]) if row else 0

    sealed = 0
    if directory.is_dir():
        for path in sorted(directory.glob(f"*{CHECKPOINT_SUFFIX}")):
            try:
                sealed = max(sealed, _checkpoint_seq(json.loads(path.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, OSError):
                continue

    if sealed < head_seq:
        return VerifyResult(
            ok=False,
            checked=chain.checked,
            broken_at=sealed,
            reason=(
                f"chain head is at {head_seq} but the newest checkpoint seals {sealed}; "
                "the last run was not sealed"
            ),
        )
    return VerifyResult(ok=True, checked=chain.checked)


def seal_run_end(
    conn: db.Connection,
    dir_path: str | Path,
    key: Ed25519PrivateKey,
    *,
    at: str | None = None,
) -> Path:
    """Seal at the end of a run, whatever the chain length (§14 b).

    Written with its own ``reason`` so it never collides with the interval seal
    at the same seq.
    """
    return write_checkpoint(conn, dir_path, key, at=at, reason="run-end")


def maybe_write_checkpoint(
    conn: db.Connection,
    dir_path: str | Path,
    key: Ed25519PrivateKey,
    *,
    at: str | None = None,
) -> Path | None:
    """Seal every :data:`CHECKPOINT_INTERVAL` entries.

    Returns the path written, or ``None`` if it was not yet time. Call
    :func:`seal_run_end` separately at the end of a run: folding it in here was
    what made the two seals overwrite one another.
    """
    # Read the head seq, not count(*). `count(*)` is a full scan of a table that
    # grows without bound: measured 0.173 s at 1M rows, on the hot path of
    # *every* append, which is a 173-second stall per write once the log is large
    # (D-B21). `ORDER BY seq DESC LIMIT 1` is the rowid and measures 0.05 ms.
    row = conn.execute("SELECT seq FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    head = int(row["seq"]) if row else 0
    if head == 0 or head % CHECKPOINT_INTERVAL != 0:
        return None
    return write_checkpoint(conn, dir_path, key, at=at, reason="interval")
