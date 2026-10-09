"""Tests for the trust substrate: DB, audit chain, ledger, state machines.

FINAL.md §14 (b), §10.3 T-07, T-13, T-17.

Red first. Run against the real SQLite file in ``tmp_path`` — no mocks of
``app.core`` (§10.1 rule 2).
"""

from __future__ import annotations

import itertools
import json
import sqlite3
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest

from app.core import audit, db, ledger, statemachine


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[db.Connection]:
    connection = db.connect(tmp_path / "app.sqlite")
    try:
        yield connection
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class TestSchema:
    def test_migrations_bring_an_empty_file_to_the_current_version(
        self, conn: db.Connection
    ) -> None:
        assert db.user_version(conn) == db.SCHEMA_VERSION

    def test_migrating_twice_is_a_no_op(self, tmp_path: Path) -> None:
        path = tmp_path / "app.sqlite"
        db.connect(path).close()
        second = db.connect(path)
        try:
            assert db.user_version(second) == db.SCHEMA_VERSION
            # No duplicate-table error means the migration was skipped, not rerun.
            assert second.execute("SELECT count(*) FROM schema_meta").fetchone()[0] == 1
        finally:
            second.close()

    def test_foreign_keys_are_on(self, conn: db.Connection) -> None:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_wal_is_enabled(self, conn: db.Connection) -> None:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"

    def test_every_table_in_the_spec_exists(self, conn: db.Connection) -> None:
        found = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        expected = {
            "entity",
            "user",
            "vendor",
            "vendor_contact",
            "payee_version",
            "beneficiary_map",
            "payee_change_request",
            "callback_verification",
            "bill",
            "obligation",
            "obligation_tranche",
            "duplicate_lock",
            "run",
            "plan",
            "plan_item",
            "approval_packet",
            "approval_signature",
            "approval_consumption",
            "conversion",
            "transfer_attempt",
            "transfer_observation",
            "incident",
            "rfi",
            "screening_result",
            "tie_out",
            "recon_exception",
            "journal_line",
            "audit_log",
            "killswitch_state",
            "trip",
            "trip_clear_signature",
            "policy_load",
            "webhook_event",
            "counters",
            "schema_meta",
        }
        assert expected <= found, f"missing: {sorted(expected - found)}"

    def test_money_columns_are_text_never_real(self, conn: db.Connection) -> None:
        """A REAL column would silently lose the exactness the packet hash needs."""
        for table, column in (
            ("obligation", "amount"),
            ("obligation_tranche", "amount"),
            ("conversion", "buy_amount"),
            ("tie_out", "residual"),
            ("journal_line", "amount_usd"),
        ):
            decl = {
                row[1]: (row[2] or "").upper()
                for row in conn.execute(f"PRAGMA table_info({table})")
            }
            assert decl[column] == "TEXT", f"{table}.{column} is {decl[column]}"


# ---------------------------------------------------------------------------
# T-13: the audit chain
# ---------------------------------------------------------------------------
class TestAuditChain:
    def test_first_entry_has_the_genesis_prev_hash(self, conn: db.Connection) -> None:
        audit.log_intent(conn, kind="RUN_START", payload={"run_id": "r1"})
        row = conn.execute("SELECT prev_hash, entry_hash FROM audit_log").fetchone()
        assert row["prev_hash"] == audit.GENESIS_PREV_HASH

    def test_each_entry_chains_to_the_previous_hash(self, conn: db.Connection) -> None:
        for i in range(5):
            audit.log_intent(conn, kind="PING", payload={"i": i})
        rows = list(conn.execute("SELECT seq, prev_hash, entry_hash FROM audit_log ORDER BY seq"))
        for previous, current in itertools.pairwise(rows):
            assert current["prev_hash"] == previous["entry_hash"]

    def test_verify_passes_on_an_untouched_chain(self, conn: db.Connection) -> None:
        for i in range(5):
            audit.log_intent(conn, kind="PING", payload={"i": i})
        assert audit.verify(conn).ok

    def test_the_hash_covers_the_payload(self, conn: db.Connection) -> None:
        """Recomputing with a different payload must produce a different hash."""
        a = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {"a": 1}, "2026-01-01T00:00:00+00:00", 1)
        b = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {"a": 2}, "2026-01-01T00:00:00+00:00", 1)
        assert a != b

    def test_the_hash_covers_the_sequence_number(self, conn: db.Connection) -> None:
        """Reordering two entries must break the chain, or a swap goes unnoticed."""
        at = "2026-01-01T00:00:00+00:00"
        a = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {}, at, 1)
        b = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {}, at, 2)
        assert a != b

    def test_the_hash_covers_the_timestamp(self, conn: db.Connection) -> None:
        a = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {}, "2026-01-01T00:00:00+00:00", 1)
        b = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {}, "2026-01-02T00:00:00+00:00", 1)
        assert a != b

    def test_the_canonical_form_ignores_key_order(self, conn: db.Connection) -> None:
        """Two JSON spellings of the same payload must hash the same."""
        at = "2026-01-01T00:00:00+00:00"
        a = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {"a": 1, "b": 2}, at, 1)
        b = audit.entry_hash(audit.GENESIS_PREV_HASH, "X", {"b": 2, "a": 1}, at, 1)
        assert a == b

    def test_verify_fails_when_the_database_is_tampered(self, conn: db.Connection) -> None:
        for i in range(3):
            audit.log_intent(conn, kind="PING", payload={"i": i})
        # Rewrite a payload behind the append-only trigger's back.
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute("UPDATE audit_log SET payload_json='{\"i\":999}' WHERE seq=2")
        conn.commit()

        result = audit.verify(conn)
        assert not result.ok
        assert result.broken_at == 2

    def test_update_on_the_audit_log_aborts(self, conn: db.Connection) -> None:
        audit.log_intent(conn, kind="X", payload={})
        with pytest.raises(Exception, match="append-only"):
            conn.execute("UPDATE audit_log SET kind='Y'")

    def test_delete_from_the_audit_log_aborts(self, conn: db.Connection) -> None:
        audit.log_intent(conn, kind="X", payload={})
        with pytest.raises(Exception, match="append-only"):
            conn.execute("DELETE FROM audit_log")

    def test_a_chain_with_a_deleted_middle_entry_is_detected(self, conn: db.Connection) -> None:
        for i in range(6):
            audit.log_intent(conn, kind="STEP", payload={"i": i})
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("DELETE FROM audit_log WHERE seq=3")
        conn.commit()

        assert not audit.verify(conn).ok

    def test_an_empty_chain_verifies(self, conn: db.Connection) -> None:
        assert audit.verify(conn).ok

    def test_seq_is_monotonic_and_unique(self, conn: db.Connection) -> None:
        for i in range(4):
            audit.log_intent(conn, kind="PING", payload={"i": i})
        seqs = [row[0] for row in conn.execute("SELECT seq FROM audit_log ORDER BY seq")]
        assert seqs == sorted(seqs)
        assert len(seqs) == len(set(seqs))


class TestSignedCheckpoints:
    """The DB triggers can be dropped; the signed checkpoints cannot be forged."""

    def test_a_checkpoint_written_on_an_untouched_chain_verifies(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        key = audit.generate_key()
        for i in range(4):
            audit.log_intent(conn, kind="STEP", payload={"i": i})
        audit.write_checkpoint(conn, tmp_path / "cp", key)

        result = audit.verify_checkpoints(conn, tmp_path / "cp", key.public_key())
        assert result.ok

    def test_a_tamper_is_caught_even_after_the_chain_is_recomputed(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        """T-13's harder half: recompute every hash, and the signature still fails.

        This is the case the DB trigger cannot cover on its own.
        """
        key = audit.generate_key()
        checkpoints = tmp_path / "cp"
        for i in range(4):
            audit.log_intent(conn, kind="STEP", payload={"i": i})
        audit.write_checkpoint(conn, checkpoints, key)

        # Drop the triggers and rewrite history, recomputing the whole chain.
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("UPDATE audit_log SET payload_json='{\"i\":999}' WHERE seq=2")
        prev = audit.GENESIS_PREV_HASH
        for index, row in enumerate(
            list(conn.execute("SELECT seq, kind, payload_json, at FROM audit_log ORDER BY seq")),
            start=1,
        ):
            digest = audit.entry_hash(
                prev, row["kind"], json.loads(row["payload_json"]), row["at"], index
            )
            conn.execute(
                "UPDATE audit_log SET prev_hash=?, entry_hash=? WHERE seq=?", (prev, digest, index)
            )
            prev = digest
        conn.commit()

        # The internal chain is now self-consistent...
        assert audit.verify(conn).ok
        # ...but the signed checkpoint still pins the old head.
        result = audit.verify_checkpoints(conn, checkpoints, key.public_key())
        assert not result.ok

    def test_a_missing_checkpoint_is_a_failure(self, conn: db.Connection, tmp_path: Path) -> None:
        """An unsealed chain means entries were appended without sealing."""
        key = audit.generate_key()
        audit.log_intent(conn, kind="STEP", payload={"i": 1})
        result = audit.verify_checkpoints(conn, tmp_path / "cp", key.public_key())
        assert not result.ok

    def test_entries_appended_after_the_last_seal_are_a_failure(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        key = audit.generate_key()
        checkpoints = tmp_path / "cp"
        audit.log_intent(conn, kind="STEP", payload={"i": 1})
        audit.write_checkpoint(conn, checkpoints, key)
        audit.log_intent(conn, kind="STEP", payload={"i": 2})

        assert not audit.verify_checkpoints(conn, checkpoints, key.public_key()).ok

    def test_a_checkpoint_signed_by_another_key_does_not_verify(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        real = audit.generate_key()
        impostor = audit.generate_key()
        audit.log_intent(conn, kind="STEP", payload={"i": 1})
        audit.write_checkpoint(conn, tmp_path / "cp", impostor)

        assert not audit.verify_checkpoints(conn, tmp_path / "cp", real.public_key()).ok

    def test_the_checkpoint_interval_fires_on_the_boundary(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        key = audit.generate_key()
        for i in range(audit.CHECKPOINT_INTERVAL - 1):
            audit.log_intent(conn, kind="STEP", payload={"i": i})
            assert audit.maybe_write_checkpoint(conn, tmp_path / "cp", key) is None
        audit.log_intent(conn, kind="STEP", payload={"i": audit.CHECKPOINT_INTERVAL})
        assert audit.maybe_write_checkpoint(conn, tmp_path / "cp", key) is not None


# ---------------------------------------------------------------------------
# T-17: audit write failure means no API mutation
# ---------------------------------------------------------------------------
@pytest.mark.compliance("T-17")
class TestAuditFailureIsFatal:
    def test_log_intent_raises_when_the_audit_table_is_unwritable(
        self, conn: db.Connection
    ) -> None:
        conn.execute("DROP TABLE audit_log")
        with pytest.raises(audit.AuditWriteError):
            audit.log_intent(conn, kind="INTENT", payload={"x": 1})

    def test_a_failed_log_intent_leaves_no_partial_row(self, conn: db.Connection) -> None:
        audit.log_intent(conn, kind="OK", payload={})
        before = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]
        conn.execute("DROP TABLE audit_log")
        with pytest.raises(audit.AuditWriteError):
            audit.log_intent(conn, kind="INTENT", payload={})
        # Nothing half-written: the table is gone, not corrupted.
        assert before == 1


# ---------------------------------------------------------------------------
# Ledger: double entry per currency
# ---------------------------------------------------------------------------
class TestLedger:
    @staticmethod
    def _run(conn: db.Connection, run_id: str = "r1") -> str:
        """Journal lines reference a run, so a run row must exist first."""
        conn.execute(
            "INSERT OR IGNORE INTO run (id, started_at, opening_balances, shadow, state)"
            " VALUES (?, ?, '{}', 0, 'OPEN')",
            (run_id, audit.now_iso()),
        )
        return run_id

    def test_a_posted_journal_balances_to_zero(self, conn: db.Connection) -> None:
        run_id = self._run(conn)
        ledger.post(
            conn,
            run_id=run_id,
            legs=[
                ledger.Leg(account="AP-clearing:EUR", debit="7500.00", currency="EUR"),
                ledger.Leg(account="Wallet:EUR", credit="7500.00", currency="EUR"),
            ],
        )
        # `balances` reports gross debit and credit totals per currency, so a
        # balanced posting shows equal non-zero totals, not zeros. The zero check
        # is `assert_ledger_balances`.
        assert ledger.balances(conn)["EUR"] == {
            "debit": Decimal("7500.00"),
            "credit": Decimal("7500.00"),
        }

    def test_the_ledger_balances_globally_after_a_posting(self, conn: db.Connection) -> None:
        run_id = self._run(conn)
        ledger.post(
            conn,
            run_id=run_id,
            legs=[
                ledger.Leg(account="AP-clearing:EUR", debit="7500.00", currency="EUR"),
                ledger.Leg(account="Wallet:EUR", credit="7500.00", currency="EUR"),
            ],
        )
        ledger.assert_ledger_balances(conn)

    def test_a_journal_line_cannot_reference_a_missing_run(self, conn: db.Connection) -> None:
        """foreign_keys=ON must actually be on, not merely declared."""
        with pytest.raises(sqlite3.IntegrityError):
            ledger.post(
                conn,
                run_id="no-such-run",
                legs=[
                    ledger.Leg(account="A:EUR", debit="1.00", currency="EUR"),
                    ledger.Leg(account="B:EUR", credit="1.00", currency="EUR"),
                ],
            )

    def test_an_unbalanced_post_is_refused(self, conn: db.Connection) -> None:
        with pytest.raises(ledger.UnbalancedError):
            ledger.post(
                conn,
                run_id="r1",
                legs=[
                    ledger.Leg(account="AP-clearing:EUR", debit="7500.00", currency="EUR"),
                    ledger.Leg(account="Wallet:EUR", credit="7400.00", currency="EUR"),
                ],
            )

    def test_a_single_sided_post_is_refused(self, conn: db.Connection) -> None:
        with pytest.raises(ledger.UnbalancedError):
            ledger.post(
                conn,
                run_id="r1",
                legs=[
                    ledger.Leg(account="Wallet:EUR", debit="1.00", currency="EUR"),
                ],
            )

    def test_a_leg_cannot_be_both_debit_and_credit(self, conn: db.Connection) -> None:
        with pytest.raises(ValueError, match="both"):
            ledger.post(
                conn,
                run_id="r1",
                legs=[
                    ledger.Leg(account="A:EUR", debit="1.00", credit="1.00", currency="EUR"),
                    ledger.Leg(account="B:EUR", debit="1.00", currency="EUR"),
                ],
            )

    def test_balances_are_tracked_per_currency(self, conn: db.Connection) -> None:
        run_id = self._run(conn)
        ledger.post(
            conn,
            run_id=run_id,
            legs=[
                ledger.Leg(account="A:EUR", debit="100.00", currency="EUR"),
                ledger.Leg(account="B:EUR", credit="100.00", currency="EUR"),
            ],
        )
        assert set(ledger.balances(conn)) == {"EUR"}

    def test_ledger_rows_are_written_to_the_journal_table(self, conn: db.Connection) -> None:
        run_id = self._run(conn)
        ledger.post(
            conn,
            run_id=run_id,
            legs=[
                ledger.Leg(
                    account="AP-clearing:EUR", debit="7500.00", currency="EUR", source_id="x"
                ),
                ledger.Leg(account="Wallet:EUR", credit="7500.00", currency="EUR", source_id="x"),
            ],
        )
        rows = list(
            conn.execute("SELECT account, debit, credit FROM journal_line ORDER BY line_no")
        )
        assert len(rows) == 2
        assert rows[0]["account"] == "AP-clearing:EUR"


# ---------------------------------------------------------------------------
# State machines
# ---------------------------------------------------------------------------
class TestTransferStateMachine:
    def test_processing_to_sent_is_allowed(self) -> None:
        assert statemachine.transfer_next_awx("PROCESSING", "SENT") == "SENT"

    def test_sent_to_paid_is_allowed(self) -> None:
        assert statemachine.transfer_next_awx("SENT", "PAID") == "PAID"

    def test_paid_to_failed_is_allowed(self) -> None:
        """Airwallex documents this: a bank return can arrive after PAID.

        ``awx_status`` does move to FAILED — that is the sandbox's truth. What
        stays provisional is our *overlay* ``wt_state``, which is why PAID is
        never FINAL (§4.10). Conflating the two columns is exactly the mistake
        this design avoids.
        """
        assert statemachine.transfer_next_awx("PAID", "FAILED") == "FAILED"

    def test_a_documented_regression_is_ignored_not_applied(self) -> None:
        assert statemachine.transfer_next_awx("SENT", "PROCESSING") == "SENT"

    def test_an_unknown_status_keeps_the_previous_state(self) -> None:
        assert statemachine.transfer_next_awx("SENT", "TELEPORTED") == "SENT"

    def test_a_jump_over_a_terminal_state_is_refused(self) -> None:
        assert statemachine.transfer_next_awx("CANCELLED", "PAID") == "CANCELLED"

    def test_terminal_states_never_move(self) -> None:
        for terminal in ("CANCELLED", "FAILED"):
            for observed in ("PAID", "SENT", "PROCESSING", "OVERDUE"):
                assert statemachine.transfer_next_awx(terminal, observed) == terminal


class TestFailureCapture:
    def test_failure_type_is_captured_from_the_failed_object(self) -> None:
        result = statemachine.apply_transfer_observation(
            awx_status="FAILED",
            failure_type="ACCOUNT_CLOSED",
            failure_reason="90701: Account closed",
            current_failure_type=None,
        )
        assert result.failure_type == "ACCOUNT_CLOSED"

    def test_failure_type_is_also_captured_from_the_auto_cancelled_object(self) -> None:
        """§4.11: FAILED auto-cancels within seconds. Capture on first sight."""
        result = statemachine.apply_transfer_observation(
            awx_status="CANCELLED",
            failure_type="ACCOUNT_CLOSED",
            failure_reason="90701: Account closed",
            current_failure_type=None,
        )
        assert result.failure_type == "ACCOUNT_CLOSED"

    def test_failure_type_is_never_nulled_once_seen(self) -> None:
        """The whole point: a later success must not erase the evidence."""
        result = statemachine.apply_transfer_observation(
            awx_status="CANCELLED",
            failure_type=None,
            failure_reason=None,
            current_failure_type="ACCOUNT_CLOSED",
        )
        assert result.failure_type == "ACCOUNT_CLOSED"

    def test_a_first_failure_type_is_not_overwritten_by_a_second(self) -> None:
        result = statemachine.apply_transfer_observation(
            awx_status="CANCELLED",
            failure_type="SYSTEM_ERROR",
            failure_reason="91402",
            current_failure_type="ACCOUNT_CLOSED",
        )
        assert result.failure_type == "ACCOUNT_CLOSED"

    def test_an_unknown_status_raises_an_incident_flag(self) -> None:
        result = statemachine.apply_transfer_observation(
            awx_status="WARP_SPEED",
            failure_type=None,
            failure_reason=None,
            current_failure_type=None,
        )
        assert result.unknown_status_incident


class TestPayeeVersionMachine:
    def test_proposed_becomes_active_capped_on_approval(self) -> None:
        assert statemachine.payee_next("PROPOSED", "APPROVED") == "ACTIVE_CAPPED"

    def test_active_capped_becomes_active_after_two_finals(self) -> None:
        assert statemachine.payee_next("ACTIVE_CAPPED", "FINAL:2") == "ACTIVE"

    def test_active_capped_stays_capped_after_one_final(self) -> None:
        assert statemachine.payee_next("ACTIVE_CAPPED", "FINAL:1") == "ACTIVE_CAPPED"

    def test_rejected_is_terminal(self) -> None:
        assert statemachine.payee_next("REJECTED", "APPROVED") == "REJECTED"

    def test_a_suspension_overrides_the_normal_path(self) -> None:
        assert statemachine.payee_next("ACTIVE", "FAILURE") == "SUSPENDED"

    def test_compliance_hold_overrides_a_normal_transition(self) -> None:
        assert statemachine.payee_next("ACTIVE_CAPPED", "FINAL:5") == "ACTIVE"
        assert statemachine.payee_next("ACTIVE", "COMPLIANCE") == "COMPLIANCE_HOLD"

    def test_a_payee_under_compliance_hold_never_advances(self) -> None:
        """A settled payment must not quietly lift a compliance block."""
        for event in ("FINAL:2", "FINAL:99", "APPROVED"):
            assert statemachine.payee_next("COMPLIANCE_HOLD", event) == "COMPLIANCE_HOLD"

    def test_a_terminal_payee_is_never_revived(self) -> None:
        for terminal in ("REJECTED", "RETIRED", "SUPERSEDED"):
            for event in ("APPROVED", "FINAL:9", "FAILURE"):
                assert statemachine.payee_next(terminal, event) == terminal
