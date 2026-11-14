"""Historical raw signature fixtures, excluded from the runtime graph."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from decimal import Decimal


def record_hash(record: Mapping[str, object]) -> str:
    """``sha256(rfc8785(record))`` - the value the recorder signs.

    The record is canonicalised so that the same callback produces the same hash in
    the UI, in the database, and in the executor's re-verification. A plain
    ``json.dumps`` would differ on whitespace or key order, and the signature would
    verify in one place and not another.
    """
    import rfc8785

    plain = _plain(record)
    return hashlib.sha256(rfc8785.dumps(plain)).hexdigest()  # type: ignore[arg-type]


class UnsignedCallbackError(PermissionError):
    """A callback row without a valid recorder signature.

    §4.5.2 rule 7 and T-10b: this counts as **no callback at all**, not as an
    unverified one. Treating it as "present but weak" would let a directly-inserted
    row take the place of a real confirmation, which is the entire threat the rule
    exists for.
    """


def verify_recorder_signature(
    *,
    record: Mapping[str, object],
    public_key: bytes | None,
    signature: bytes | None,
    nonce_used: bool = False,
    signing_method: str = "",
) -> str:
    """Verify a callback's recorder signature, or refuse.

    ``public_key`` is ``None`` when the recorder's passkey is not registered - which
    is refused, not skipped. An absent credential cannot pass a rule whose whole
    purpose is to prove *this person* signed it.

    A reused nonce is also refused, even before the signature check: §4.5.2 rule 7
    makes the challenge single-use for the same reason §4.8 does, which is that a
    replayed signature would otherwise be indistinguishable from a fresh one.
    """
    if not signature or public_key is None:
        raise UnsignedCallbackError(
            "a callback without the recorder's signature counts as no callback at "
            "all (FINAL.md §4.5.2 rule 7, T-10b)"
        )
    if nonce_used:
        raise UnsignedCallbackError(
            "the recorder's nonce has been used before. The challenge is single "
            "use so a replayed signature cannot stand in for a fresh one."
        )

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
    except ValueError:
        raise UnsignedCallbackError("the recorder signature is not valid hex") from None

    if not _verified(key, signature, _digest_input(record)):
        raise UnsignedCallbackError("the recorder signature does not match the callback record")

    if signing_method == "HMAC_FALLBACK":
        # Labelled, never silently equal to a passkey signature.
        return "cli_hmac"
    return "ui_passkey"


def _verified(key: object, signature: bytes, digest: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature

    try:
        key.verify(signature, digest)  # type: ignore[attr-defined]
    except InvalidSignature:
        return False
    return True


def _digest_input(record: Mapping[str, object]) -> bytes:
    """The exact bytes the signature covers: the record hash, ascii."""
    digest_hex = record_hash(record)
    return digest_hex.encode("ascii")


def _plain(value: object) -> object:
    """Canonicalise a record for hashing: floats refused, Decimals as strings.

    Recursive and total: a Mapping becomes a sorted plain dict, a sequence becomes a
    plain list, and every other type is either passed through or refused. Rfc8785's
    ``dumps`` accepts the result; the ``cast`` at the call site is what tells mypy so,
    because its accepted type is narrower than this module's ``object``.
    """
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, str)):
        return value
    from app.money import raise_on_float

    raise_on_float({"value": value}, "callback record")
    return str(value)
