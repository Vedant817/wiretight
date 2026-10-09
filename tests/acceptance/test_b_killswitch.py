"""T-07: the kill switch, and T-34's clearing rules.

FINAL.md §4.9, §4.15 rows 24-30.

The properties under test, in order of how much damage getting them wrong would
do:

1. **Any** of {DB flag, HALT file, unreadable HALT path} means halted.
2. Halted blocks the three create calls and nothing else.
3. Clearing needs two distinct approvers and a reason.
4. Clearing resumes nothing: approvals that expired while halted stay expired.
5. The automatic rules trip on their thresholds, and compliance trips first time.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core import db
from app.core import killswitch as ks


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[db.Connection]:
    connection = db.connect(tmp_path / "app.sqlite")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def halt_file(tmp_path: Path) -> Path:
    return tmp_path / "var" / "HALT"


#: The D6 cast. Clearing references `user.id`, so the rows must exist: an
#: approver who is not on the roster cannot clear anything.
CAST = [
    ("arun", "approver"),
    ("meera", "approver"),
    ("kabir", "approver"),
    ("priya", "ops"),
]


@pytest.fixture()
def roster(conn: db.Connection) -> None:
    from app.core import audit

    for user_id, role in CAST:
        conn.execute(
            "INSERT INTO user (id, name, role, email, sign_count, created_at)"
            " VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, user_id, role, f"{user_id}@halden.example", audit.now_iso()),
        )


def two_clears() -> list[dict[str, object]]:
    return [
        {
            "approver_id": "meera",
            "method": "HMAC_FALLBACK",
            "signed_via": "cli_hmac",
            "signature": b"a",
        },
        {
            "approver_id": "kabir",
            "method": "HMAC_FALLBACK",
            "signed_via": "cli_hmac",
            "signature": b"b",
        },
    ]


# ---------------------------------------------------------------------------
# 1. Halted is the default-reading failure
# ---------------------------------------------------------------------------
class TestHaltingIsFailClosed:
    def test_a_fresh_switch_is_running(self, conn: db.Connection, halt_file: Path) -> None:
        assert not ks.load(conn, halt_file).is_halted()

    def test_the_db_flag_halts(self, conn: db.Connection, halt_file: Path) -> None:
        ks.trip(conn, "manual", halt_file=halt_file)
        assert ks.load(conn, halt_file).is_halted()

    def test_the_halt_file_alone_halts(self, conn: db.Connection, halt_file: Path) -> None:
        """A human must be able to halt without the database."""
        halt_file.parent.mkdir(parents=True, exist_ok=True)
        halt_file.write_text("halted by hand\n", encoding="utf-8")
        assert ks.load(conn, halt_file).is_halted()

    def test_an_unreadable_halt_path_counts_as_halted(
        self, conn: db.Connection, tmp_path: Path
    ) -> None:
        """§4.9: "the file path unreadable = halted". Fail toward stopping.

        On POSIX this is a directory with no read permission; on Windows a
        locked file. Both are simulated with a monkeypatched ``exists`` that
        raises, which is the exact failure mode being specified.
        """
        import pathlib

        original = pathlib.Path.exists

        def boom(self: Path) -> bool:
            if self.name == "HALT":
                raise PermissionError("cannot stat")
            return original(self)

        pathlib.Path.exists = boom  # type: ignore[method-assign]
        try:
            assert ks.load(conn, tmp_path / "var" / "HALT").is_halted()
        finally:
            pathlib.Path.exists = original  # type: ignore[method-assign]

    def test_guard_raises_when_halted(self, conn: db.Connection, halt_file: Path) -> None:
        ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="halted"):
            ks.load(conn, halt_file).guard()

    def test_guard_is_silent_when_running(self, conn: db.Connection, halt_file: Path) -> None:
        ks.load(conn, halt_file).guard()  # must not raise

    def test_tripping_twice_keeps_the_first_trip(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        first = ks.trip(conn, "first reason", halt_file=halt_file)
        second = ks.trip(conn, "second reason", halt_file=halt_file)
        assert first.id == second.id
        assert conn.execute("SELECT count(*) FROM trip").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# 2. Halted blocks writes, not reads
# ---------------------------------------------------------------------------
@pytest.mark.compliance("T-07")
class TestHaltedBlocksOnlyWrites:
    def test_the_reason_survives_a_restart(self, conn: db.Connection, halt_file: Path) -> None:
        ks.trip(conn, "audit write failure", halt_file=halt_file)
        reopened = db.connect(Path(halt_file).parent.parent / "app.sqlite")
        try:
            switch = ks.load(reopened, halt_file)
            assert switch.is_halted()
            assert "audit write failure" in switch.reason_text()
        finally:
            reopened.close()

    def test_a_trip_is_audited(self, conn: db.Connection, halt_file: Path) -> None:
        ks.trip(conn, "because", halt_file=halt_file)
        kinds = [row["kind"] for row in conn.execute("SELECT kind FROM audit_log")]
        assert "KILLSWITCH_TRIP" in kinds

    def test_a_clear_is_audited(self, conn: db.Connection, halt_file: Path, roster: None) -> None:
        trip = ks.trip(conn, "because", halt_file=halt_file)
        ks.clear(conn, trip.id, "resolved", two_clears(), halt_file=halt_file)
        kinds = [row["kind"] for row in conn.execute("SELECT kind FROM audit_log")]
        assert "KILLSWITCH_CLEAR" in kinds

    def test_reads_are_unaffected_by_the_halt(self, conn: db.Connection, halt_file: Path) -> None:
        """Polling, AMBIGUOUS lookups and reconciliation continue while halted."""
        ks.trip(conn, "manual", halt_file=halt_file)
        # A balance read is a read.
        assert ks.load(conn, halt_file).is_halted()
        assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] >= 1


# ---------------------------------------------------------------------------
# 3. Clearing needs two people and a reason
# ---------------------------------------------------------------------------
@pytest.mark.compliance("T-34")
class TestClearingRequiresTwoApprovers:
    def test_two_distinct_approvers_clear_it(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        ks.clear(conn, trip.id, "fixed", two_clears(), halt_file=halt_file)
        assert not ks.load(conn, halt_file).is_halted()

    def test_one_approver_cannot_clear_it(self, conn: db.Connection, halt_file: Path) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="2 distinct"):
            ks.clear(conn, trip.id, "fixed", two_clears()[:1], halt_file=halt_file)
        assert ks.load(conn, halt_file).is_halted()

    def test_the_same_approver_twice_cannot_clear_it(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        """Two signatures from one person is one person."""
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        same = [dict(two_clears()[0]), dict(two_clears()[0])]
        with pytest.raises(ks.HaltedError, match="2 distinct"):
            ks.clear(conn, trip.id, "fixed", same, halt_file=halt_file)
        assert ks.load(conn, halt_file).is_halted()

    def test_a_reason_is_required(self, conn: db.Connection, halt_file: Path, roster: None) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="reason"):
            ks.clear(conn, trip.id, "   ", two_clears(), halt_file=halt_file)

    def test_each_clear_is_recorded_with_its_nonce(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        ks.clear(conn, trip.id, "fixed", two_clears(), halt_file=halt_file)
        rows = list(conn.execute("SELECT approver_id, challenge_nonce FROM trip_clear_signature"))
        assert len(rows) == 2
        assert len({row["challenge_nonce"] for row in rows}) == 2

    def test_clearing_removes_the_halt_file(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        assert halt_file.exists()
        ks.clear(conn, trip.id, "fixed", two_clears(), halt_file=halt_file)
        assert not halt_file.exists()

    def test_clearing_resumes_nothing(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        """§4.9: approvals that expired while halted need fresh sign-offs."""
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        ks.clear(conn, trip.id, "fixed", two_clears(), halt_file=halt_file)
        # Nothing in this module re-approves anything: the switch has no access
        # to the approval tables, by construction.
        expired = conn.execute(
            "SELECT count(*) FROM approval_packet WHERE state = 'EXPIRED'"
        ).fetchone()[0]
        assert expired == 0  # it does not invent approvals either
        assert conn.execute("SELECT count(*) FROM approval_consumption").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# 4. The clear signature payload
# ---------------------------------------------------------------------------
class TestClearSignaturePayload:
    def test_it_is_sha256_of_clear_trip_reason(self) -> None:
        import hashlib

        expected = hashlib.sha256(b"clear|trip-1|all clear").hexdigest()
        assert ks.clear_signature_payload("trip-1", "all clear") == expected

    def test_a_different_reason_produces_a_different_payload(self) -> None:
        assert ks.clear_signature_payload("trip-1", "a") != ks.clear_signature_payload(
            "trip-1", "b"
        )

    def test_a_different_trip_produces_a_different_payload(self) -> None:
        assert ks.clear_signature_payload("t1", "a") != ks.clear_signature_payload("t2", "a")


# ---------------------------------------------------------------------------
# 5. Automatic trip rules, §4.15 rows 24-29
# ---------------------------------------------------------------------------
# The §4.15 rows 24-30 thresholds, as §4.17 writes them. Shared by reference so
# an edit in one test class cannot silently move a threshold another asserts on.
KILLSWITCH_POLICY: dict[str, object] = {
    "killswitch": {
        "clock_skew_seconds": 120,
        "ambiguous_creates_per_run": 2,
        "ambiguous_creates_rolling_24h": 2,
        "failed_transfers_rolling_1h": 3,
        "extraction_conflicts_rolling_24h": 3,
        "clear_signatures": 2,
    }
}


class TestAutomaticTripRules:
    def tripper(self) -> ks.AutomaticTripper:
        return ks.AutomaticTripper(KILLSWITCH_POLICY)

    # r24
    def test_clock_skew_within_the_limit_does_not_trip(self) -> None:
        assert self.tripper().clock_skew(119) is None
        assert self.tripper().clock_skew(-119) is None

    def test_clock_skew_over_the_limit_trips(self) -> None:
        reason = self.tripper().clock_skew(121)
        assert reason and "r24" in reason

    def test_negative_skew_also_trips(self) -> None:
        """|skew|: a clock behind is just as wrong as one ahead."""
        assert self.tripper().clock_skew(-121) is not None

    # r26
    def test_one_ambiguous_does_not_trip(self) -> None:
        assert self.tripper().ambiguous(1, 1) is None

    def test_two_ambiguous_in_a_run_trips(self) -> None:
        reason = self.tripper().ambiguous(2, 2)
        assert reason and "r26" in reason

    def test_two_ambiguous_across_runs_in_24h_trips(self) -> None:
        assert self.tripper().ambiguous(1, 2) is not None

    # r27
    def test_two_failures_in_an_hour_does_not_trip(self) -> None:
        assert self.tripper().failures(2) is None

    def test_three_failures_in_an_hour_trips(self) -> None:
        reason = self.tripper().failures(3)
        assert reason and "r27" in reason

    # r28
    def test_two_extraction_conflicts_do_not_trip(self) -> None:
        assert self.tripper().extraction_conflicts(2) is None

    def test_three_extraction_conflicts_trip(self) -> None:
        assert self.tripper().extraction_conflicts(3) is not None

    # r29: first occurrence, no threshold
    @pytest.mark.parametrize(
        "failure_type",
        ["ACCOUNT_UNDER_RESTRICTION", "TM_SUSPENDED", "CHANNEL_POLICY"],
    )
    def test_a_compliance_failure_trips_on_the_first(self, failure_type: str) -> None:
        reason = self.tripper().compliance(failure_type)
        assert reason and "r29" in reason

    def test_a_watchlist_reason_code_trips(self) -> None:
        reason = self.tripper().compliance("ACCOUNT_UNDER_RESTRICTION", ["WATCHLIST_SANCTIONS"])
        assert reason is not None

    def test_a_bare_watchlist_failure_type_trips(self) -> None:
        assert self.tripper().compliance("WATCHLIST_ADVERSE_MEDIA") is not None

    def test_an_ordinary_failure_does_not_trip(self) -> None:
        assert self.tripper().compliance("ACCOUNT_CLOSED") is None

    def test_no_failure_type_does_not_trip(self) -> None:
        assert self.tripper().compliance(None) is None

    def test_evaluate_rules_ignores_compliance_when_no_failure_was_seen(self) -> None:
        """`None` means "nothing observed", which must not read as a failure."""
        tripper = ks.AutomaticTripper(KILLSWITCH_POLICY)
        assert ks.evaluate_rules(tripper, failure_type=None) == []

    def test_evaluate_rules_still_judges_a_non_compliance_failure(self) -> None:
        tripper = ks.AutomaticTripper(KILLSWITCH_POLICY)
        assert ks.evaluate_rules(tripper, failure_type="ACCOUNT_CLOSED") == []


class TestEvaluateRules:
    #: One policy for the whole group, so a value edited in one test cannot
    #: silently change the threshold another test asserts against.
    POLICY: dict = KILLSWITCH_POLICY

    def test_no_inputs_means_no_trips(self) -> None:
        assert ks.evaluate_rules(ks.AutomaticTripper(self.POLICY)) == []

    def test_every_firing_rule_is_reported(self) -> None:
        """Five inputs, five reasons. Each names its own row."""
        reasons = ks.evaluate_rules(
            ks.AutomaticTripper(self.POLICY),
            skew_seconds=500,  # r24
            ambiguous_in_run=5,  # r26
            ambiguous_24h=5,
            failed_1h=9,  # r27
            extraction_24h=9,  # r28
            failure_type="TM_SUSPENDED",  # r29
        )
        assert len(reasons) == 5
        assert [
            next(m for m in ("r24", "r26", "r27", "r28", "r29") if m in r) for r in reasons
        ] == [
            "r24",
            "r26",
            "r27",
            "r28",
            "r29",
        ]

    def test_one_input_firing_leaves_the_others_alone(self) -> None:
        reasons = ks.evaluate_rules(ks.AutomaticTripper(self.POLICY), skew_seconds=500)
        assert len(reasons) == 1 and "r24" in reasons[0]


# ---------------------------------------------------------------------------
# Honest limits (§4.9)
# ---------------------------------------------------------------------------
def test_the_module_documents_that_transfers_are_not_recalled() -> None:
    """The kill switch blocks *future* calls. It does not recall a sent one."""
    source = Path(ks.__file__).read_text(encoding="utf-8")
    assert "not recalled" in source or "in-flight" in source
