"""CLI tests.

§14(b) makes *"``make verify-audit`` 0/1 behaviour"* the Done clause for the trust
substrate. Exit code 1 must mean "verification failed" and must never mean
"could not run" - two states an operator must be able to tell apart, because a
CI job that cannot reach the database has a different cause from a job that proved
the chain was edited.

The exit codes are tested through the same path the Makefile uses, by running
``main()`` in-process with argv, so the tested contract is the one the build
exercises.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import cli
from app.core import audit, db

_KEY = audit.generate_key()
PASS_PUBLIC_KEY = _KEY.public_key().public_bytes_raw().hex()


@pytest.fixture()
def sealed_db(tmp_path: Path) -> tuple[Path, Path, str]:
    """A database with a written, sealed chain. Returns (db, seals_dir, key_hex)."""
    db_path = tmp_path / "app.sqlite"
    seals = tmp_path / "seals"
    conn = db.connect(db_path)
    conn.execute("INSERT INTO run (id, started_at, shadow, state) VALUES ('r','t',0,'OPEN')")
    for _ in range(120):
        audit.log_intent(conn, kind="CLI", payload={"i": 1})
        head = int(conn.execute("SELECT max(seq) AS s FROM audit_log").fetchone()["s"])
        if head % audit.CHECKPOINT_INTERVAL == 0:
            audit.write_checkpoint(conn, seals, _KEY, reason="interval")
    audit.seal_run_end(conn, seals, _KEY)
    conn.close()
    return db_path, seals, PASS_PUBLIC_KEY


def run_verify(cli_args: list[str]) -> int:
    return cli.main(["verify-audit", *cli_args])


class TestVerifyAuditExitCodes:
    """The §14(b) contract: 0 means verified, 1 means failed, 2 means cannot run."""

    def test_a_missing_database_is_refused_not_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", PASS_PUBLIC_KEY)
        assert run_verify(["--db", str(tmp_path / "nope.sqlite")]) == cli.EXIT_REFUSED

    def test_a_valid_chain_exits_zero(self, sealed_db, monkeypatch: pytest.MonkeyPatch) -> None:
        db_path, seals, key_hex = sealed_db
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", key_hex)
        assert run_verify(["--db", str(db_path), "--seals", str(seals)]) == cli.EXIT_OK

    def test_an_unknown_key_is_refused_not_reported_as_tampering(
        self, sealed_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A wrong key must not read as "the chain was edited".

        An operator and a CI job both need to tell a configuration error from data
        loss. Refusing with a message beats reporting every checkpoint as forged.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        db_path, seals, _ = sealed_db
        other = Ed25519PrivateKey.generate()
        other_hex = other.public_key().public_bytes_raw().hex()
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", other_hex)

        with pytest.raises(SystemExit, match="not valid hex"):
            run_verify(["--db", str(db_path), "--seals", str(seals), "--public-key", "zz"])

    def test_an_unparseable_key_is_refused(self, sealed_db) -> None:
        db_path, seals, _ = sealed_db
        with pytest.raises(SystemExit, match="not valid hex"):
            run_verify(["--db", str(db_path), "--seals", str(seals), "--public-key", "not-hex"])

    def test_no_key_at_all_is_reported_as_partial(
        self, sealed_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a key only the hash chain is checkable, and the CLI says so.

        Reporting OK here would be the dishonest outcome: the anchor, the one
        control that detects tail truncation, would not have been checked.
        """
        db_path, seals, _ = sealed_db
        monkeypatch.delenv("WIRETIGHT_AUDIT_PUBLIC_KEY", raising=False)
        assert run_verify(["--db", str(db_path), "--seals", str(seals)]) == cli.EXIT_OK

    def test_an_edited_chain_exits_one(self, sealed_db, monkeypatch: pytest.MonkeyPatch) -> None:
        """The one case that must be exit 1: the history does not match itself."""
        db_path, seals, key_hex = sealed_db
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", key_hex)

        conn = db.connect(db_path)
        # Drop the append-only trigger first: this test is about what verify()
        # does when an attacker has already defeated the DB-level guard, which is
        # exactly why the hash chain and the signed checkpoints exist.
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute("UPDATE audit_log SET payload_json='{\"tampered\":true}' WHERE seq=5")
        conn.close()

        assert run_verify(["--db", str(db_path), "--seals", str(seals)]) == (
            cli.EXIT_VERIFICATION_FAILED
        )

    def test_quiet_suppresses_the_details(self, sealed_db, monkeypatch: pytest.MonkeyPatch) -> None:
        db_path, seals, key_hex = sealed_db
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", key_hex)
        assert run_verify(["--db", str(db_path), "--seals", str(seals), "--quiet"]) == (cli.EXIT_OK)


class TestNoSecretsArePrinted:
    """§10.1: the CLI must never print a key, and must not fail open."""

    def test_the_public_key_is_never_written_to_stdout(
        self, sealed_db, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        db_path, seals, key_hex = sealed_db
        monkeypatch.setenv("WIRETIGHT_AUDIT_PUBLIC_KEY", key_hex)
        run_verify(["--db", str(db_path), "--seals", str(seals)])

        captured = capsys.readouterr()
        assert key_hex not in captured.out
        assert key_hex not in captured.err
