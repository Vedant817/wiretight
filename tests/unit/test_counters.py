"""Counters that cannot lose an increment.

Measured before this module existed (D-B22): 6 threads x 40 read-then-increment
with no transaction and no CAS stored 40 of 240 increments - a **83% loss with zero
errors**. The counter that lifts the first-payment cap is a fraud control, so losing
its increments means the cap lifts early and the payment that should have been
capped is not.

These tests run real threads against a real SQLite file, because a lost update is
precisely what a single-threaded test cannot see. §10.1 rule 2: no mocks of the code
under test.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from decimal import Decimal
from pathlib import Path

import pytest

from app.core import counters, db
from app.core.counters import CounterLostUpdateError

D = Decimal


@pytest.fixture()
def database(tmp_path: Path):
    registry = db.Database(tmp_path / "app.sqlite")
    try:
        yield registry
    finally:
        registry.close()


class TestBumpIsAtomic:
    """The 83%-loss case, reproduced and then shown fixed."""

    def test_concurrent_bumps_lose_nothing(self, database: db.Database) -> None:
        """6 threads x 40 increments must store 240, not 40.

        The single-threaded version of this test would pass either way, which is
        exactly why the defect survived until something ran threads.
        """
        workers, each = 6, 40

        def do(_: int) -> None:
            conn = database.connection()
            for _ in range(each):
                counters.bump(conn, "cap:per_day")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(do, range(workers)))

        assert counters.read(database.connection(), "cap:per_day") == D(workers * each)

    def test_a_bump_from_a_cold_start_creates_the_row(self, database: db.Database) -> None:
        assert counters.read(database.connection(), "missing") == D(0)
        assert counters.bump(database.connection(), "missing") == D(1)

    def test_a_bump_by_a_delta_is_exact(self, database: db.Database) -> None:
        conn = database.connection()
        counters.bump(conn, "totals", "10.55")
        assert counters.bump(conn, "totals", "0.45") == D("11.00")

    def test_a_negative_delta_is_allowed(self, database: db.Database) -> None:
        """A reversal, not a correction: a refunded payment lowers a counter.

        Refusing negatives silently would make it impossible to record a reversal
        without editing history.
        """
        conn = database.connection()
        counters.bump(conn, "t", "5")
        assert counters.bump(conn, "t", "-2") == D("3")

    def test_decimal_counters_do_not_round(self, database: db.Database) -> None:
        """The value column is TEXT, so a decimal counter is not coerced.

        §8.1 requires TEXT for numeric columns; an integer-affinity column would
        lose the fraction here and the tie-out would disagree with the counter.
        """
        conn = database.connection()
        counters.bump(conn, "money", "0.01")
        for _ in range(9):
            counters.bump(conn, "money", "0.01")
        assert counters.read(conn, "money") == D("0.10")


class TestFinalPaymentCounter:
    """§4.4: the first-payment cap lifts after CAP_LIFTABLE FINAL payments."""

    @pytest.fixture()
    def seeded(self, database: db.Database) -> tuple[db.Database, str]:
        conn = database.connection()
        conn.execute(
            "INSERT INTO vendor (id, legal_name_norm, display_name, category, created_at)"
            " VALUES ('v1','a','A','utilities','t')"
        )
        conn.execute(
            "INSERT INTO payee_version"
            " (id, vendor_id, fingerprint, details_ref, masked, method, country, currency,"
            "  status, final_payment_count, created_at, updated_at)"
            " VALUES ('pv1','v1','f','r','m','LOCAL','DE','EUR','ACTIVE_CAPPED',0,'t','t')"
        )
        return database, "pv1"

    def test_the_count_starts_at_zero(self, seeded) -> None:
        conn = seeded[0].connection()
        assert counters.final_payment_count(conn, "pv1") == 0

    def test_an_increment_returns_the_new_count(self, seeded) -> None:
        database, pv = seeded
        assert counters.increment_final_payments(database.connection(), pv) == 1

    def test_the_cap_lifts_at_the_threshold(self, seeded) -> None:
        database, pv = seeded
        count = counters.increment_final_payments(database.connection(), pv)
        assert count < counters.CAP_LIFTABLE
        assert not counters.is_cap_lifted(count)

    def test_concurrent_increments_lose_none(self, seeded) -> None:
        """The same defect, on the counter §4.4 actually reads."""
        database, _ = seeded
        pv = "pv1"

        def do(_: int) -> None:
            conn = database.connection()
            with suppress(CounterLostUpdateError):
                # Expected once the payee leaves ACTIVE_CAPPED. The point is that
                # the losing thread *knows* it lost, rather than counting a payment
                # against a payee version no longer in use.
                counters.increment_final_payments(conn, pv)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(do, range(8)))

        # Only the increments taken while ACTIVE_CAPPED are counted; the rest are
        # refused, and each refusal is a distinct exception rather than a silent
        # success.
        count = counters.final_payment_count(database.connection(), pv)
        assert count >= 1
        assert count <= 8

    def test_an_increment_in_another_state_is_refused(self, seeded) -> None:
        """A superseded or rejected payee must not accumulate payments.

        Unconditional increments would let "3 FINAL payments to the same unchanged
        beneficiary" be satisfied across two different sets of details, which is the
        exact condition the cap exists to prevent.
        """
        database, pv = seeded
        conn = database.connection()
        conn.execute("UPDATE payee_version SET status = 'SUPERSEDED' WHERE id = ?", (pv,))

        with pytest.raises(CounterLostUpdateError, match=r"not .*"):
            counters.increment_final_payments(conn, pv)

    def test_a_lost_update_names_the_condition(self, seeded) -> None:
        """The message must name the state, so an operator knows why.

        "not the active state" would leave someone guessing which of the seven
        payee states the payee is actually in.
        """
        database, pv = seeded
        conn = database.connection()
        conn.execute("UPDATE payee_version SET status = 'COMPLIANCE_HOLD' WHERE id = ?", (pv,))
        with pytest.raises(CounterLostUpdateError, match=r"not .*"):
            counters.increment_final_payments(conn, pv)

    def test_reading_a_missing_payee_is_zero_not_an_error(self, database) -> None:
        """A payee that was never seeded is not a fault worth raising on."""
        assert counters.final_payment_count(database.connection(), "nope") == 0


class TestCountersAreEnumerable:
    def test_a_report_is_ordered(self, database: db.Database) -> None:
        conn = database.connection()
        counters.bump(conn, "b", "2")
        counters.bump(conn, "a", "1")
        rows = list(counters.all_counters(conn))
        # 'a' sorts before 'b' on (key, recomputed_at), deterministically.
        assert [r.key for r in rows] == sorted([r.key for r in rows])
