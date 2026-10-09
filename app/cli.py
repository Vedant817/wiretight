"""Command line entry point.

``python -m app.cli <command>``. The only command that exists today is
``verify-audit``, because §14(b) makes *"``make verify-audit`` 0/1 behaviour"*
the Done clause for the trust substrate, and the Makefile already calls this
module. Commands that reach a network or a secret are added here and nowhere else,
so the CLI stays the single place that can leak a key and the single place an
audit has to review.

Exit codes are the contract:

* ``0`` - verified, or the command completed;
* ``1`` - verification **failed**. This is the §14(b) requirement and must never
  be ``0``;
* ``2`` - the command needs credentials it does not have, or the target is not
  the sandbox.

``2`` is deliberately not ``1``: a CI job that cannot reach the database has a
different cause from a job that proved the chain was tampered with, and the
Makefile's live targets use it to refuse to run without ``CONFIRM_LIVE=1``.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.config import WorkerSettings
from app.core import audit, db

#: Exit code: the command completed and verification passed.
EXIT_OK = 0
#: Exit code: verification failed. Must never be 0 (FINAL.md §14 b).
EXIT_VERIFICATION_FAILED = 1
#: Exit code: refused - missing credentials, wrong environment, not sandbox.
EXIT_REFUSED = 2


def build_parser() -> argparse.ArgumentParser:
    """The command line. ``help`` text is generated from these choices."""
    parser = argparse.ArgumentParser(
        prog="wiretight",
        description="Wiretight: bank details stay locked until a second person confirms.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser(
        "verify-audit",
        help="verify the audit chain against signed checkpoints and the head anchor",
    )
    verify.add_argument(
        "--db",
        default=None,
        help="database path (default $WIRETIGHT_DB, else var/wiretight.sqlite)",
    )
    verify.add_argument(
        "--seals",
        default=None,
        help="directory holding signed checkpoints (default $WIRETIGHT_SEALS, else var/seals)",
    )
    verify.add_argument(
        "--public-key",
        default=None,
        help="Ed25519 public key hex (default $WIRETIGHT_AUDIT_PUBLIC_KEY)",
    )
    verify.add_argument(
        "--quiet", action="store_true", help="print only the verdict, not the details"
    )

    return parser


def _audit_key() -> str | None:
    """The Ed25519 public key as hex, from the environment only.

    Read from the environment rather than from a file any process could also
    write: a key sitting in the working directory is a key that can be edited.
    It is never printed - a stray echo of a key is a leaked key.
    """
    raw = os.environ.get("WIRETIGHT_AUDIT_PUBLIC_KEY", "").strip()
    return raw or None


def cmd_verify_audit(args: argparse.Namespace) -> int:
    """Run the full verification and report it honestly, including why it failed.

    The checks are reported separately rather than as one boolean, because "the
    chain is fine and the anchor is missing" and "the chain was edited" need
    different responses from an operator, and collapsing them into one message
    leaves nothing to act on.
    """
    settings = WorkerSettings()
    database_path = args.db or settings.app_db_path
    seals_dir = args.seals or "var/seals"
    public_key_hex = args.public_key if args.public_key else _audit_key()

    if not Path(database_path).exists():
        print(f"no database at {database_path}; nothing to verify", file=sys.stderr)
        return EXIT_REFUSED

    conn = db.connect(database_path, read_only=True)
    try:
        chain = audit.verify(conn)
        if not args.quiet:
            print(f"chain: {chain.checked} entries, {'OK' if chain.ok else 'BROKEN'}")
            if not chain.ok:
                print(f"  reason: {chain.reason}")
                if chain.broken_at:
                    print(f"  broken at seq {chain.broken_at}")

        if public_key_hex is None:
            # Without the key the strongest claim available is the hash chain.
            print(
                "no audit public key: $WIRETIGHT_AUDIT_PUBLIC_KEY is unset, so only "
                "the hash chain was checked. Checkpoint signatures and the head "
                "anchor were NOT verified (FINAL.md §14 b).",
                file=sys.stderr,
            )
            return EXIT_VERIFICATION_FAILED if not chain.ok else EXIT_OK

        key: Ed25519PublicKey = _load_public_key(public_key_hex)
        result = audit.verify_checkpoints(conn, seals_dir, key)
        if not args.quiet:
            print(f"checkpoints: {'OK' if result.ok else 'FAILED'} ({result.checked} verified)")
            if not result.ok:
                print(f"  reason: {result.reason}")
                if result.broken_at:
                    print(f"  broken at seq {result.broken_at}")

        if result.ok and not args.quiet:
            sealed = audit.head_is_sealed(conn, seals_dir)
            print(f"head sealed: {'yes' if sealed.ok else 'no'}")
            if not sealed.ok:
                print(f"  {sealed.reason}")

        return EXIT_VERIFICATION_FAILED if not result.ok else EXIT_OK
    finally:
        conn.close()


def _load_public_key(hex_key: str) -> Ed25519PublicKey:
    """Build the Ed25519 public key from hex, refusing an unparseable one.

    Refusing rather than defaulting matters: verifying against a mangled key would
    report every checkpoint as forged, and an operator would read that as tampering
    rather than as a configuration error.
    """

    try:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_key))
    except ValueError as exc:
        raise SystemExit(
            "the audit public key is not valid hex; refusing to verify against an unparseable key"
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    handlers = {"verify-audit": cmd_verify_audit}
    handler = handlers[args.command]
    return handler(args)


EXIT_OK = 0

if __name__ == "__main__":  # pragma: no cover - the process entry point
    raise SystemExit(main())
