"""T-07: the kill switch, and T-34's clearing rules.

FINAL.md §4.9, §4.15 rows 24-30.

Four of these tests exist because review found the behaviour wrong, not because
the specification was ambiguous. Each names the defect it pins down:

* a switch object must not cache the DB flag (§4.8 step 1 runs per mutating call);
* clearing must reject a stale ``trip_id``;
* clearing must be one transaction, so a failure cannot half-clear it;
* clearing must verify a signature per approver, not count strings.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core import db
from tests.support import legacy_killswitch as ks


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
CAST = [("arun", "approver"), ("meera", "approver"), ("kabir", "approver"), ("priya", "ops")]


@pytest.fixture()
def roster(conn: db.Connection) -> None:
    from app.core import audit

    for user_id, role in CAST:
        conn.execute(
            "INSERT INTO user (id, name, role, email, sign_count, created_at)"
            " VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, user_id, role, f"{user_id}@halden.example", audit.now_iso()),
        )


def clears(trip_id: str, reason: str, approvers: tuple[str, ...] = ("meera", "kabir")) -> list:
    """Valid signed clears. Used wherever the signature is not the subject."""
    return [ks.sign_clear(trip_id, reason, approver) for approver in approvers]


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
        self, conn: db.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """§4.9: "the file path unreadable = halted". Fail toward stopping.

        Simulated by making the existence check raise, which is the shape of the
        production failure (a permissions error or a broken mount) without
        depending on platform-specific ways to provoke one.
        """
        import pathlib

        real_exists = pathlib.Path.exists
        target = tmp_path / "var" / "HALT"

        def boom(self: Path) -> bool:
            if self == target:
                raise PermissionError("cannot stat")
            return real_exists(self)

        monkeypatch.setattr(pathlib.Path, "exists", boom)
        assert ks.load(conn, target).is_halted()

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


@pytest.mark.compliance("T-07")
class TestSwitchIsNeverCached:
    """§4.8 step 1 runs before *every* mutating call, so state must be re-read.

    The first version snapshotted the DB flag at load time. An executor holding
    one switch object for a run would then never see a trip raised mid-run, which
    is exactly the moment the switch matters.
    """

    def test_a_switch_loaded_before_a_trip_sees_the_trip(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        switch = ks.load(conn, halt_file)
        assert not switch.is_halted()
        ks.trip(conn, "tripped after the switch was loaded", halt_file=halt_file)
        assert switch.is_halted(), "the switch cached its state"

    def test_guard_raises_for_a_switch_loaded_before_the_trip(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        switch = ks.load(conn, halt_file)
        ks.trip(conn, "mid-run trip", halt_file=halt_file)
        with pytest.raises(ks.HaltedError):
            switch.guard()

    def test_a_switch_sees_its_own_clearing(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        switch = ks.load(conn, halt_file)
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        assert switch.is_halted()
        ks.clear(conn, trip.id, "resolved", clears(trip.id, "resolved"), halt_file=halt_file)
        assert not switch.is_halted()


# ---------------------------------------------------------------------------
# 2. Halted blocks writes, not reads
# ---------------------------------------------------------------------------
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
        ks.clear(conn, trip.id, "resolved", clears(trip.id, "resolved"), halt_file=halt_file)
        kinds = [row["kind"] for row in conn.execute("SELECT kind FROM audit_log")]
        assert "KILLSWITCH_CLEAR" in kinds

    def test_the_audit_chain_still_verifies_while_halted(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        """Reads continue: a halted executor must still be able to prove its history."""
        from app.core import audit

        ks.trip(conn, "manual", halt_file=halt_file)
        assert audit.verify(conn).ok

    def test_the_active_trip_is_readable_while_halted(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        assert ks.load(conn, halt_file).active_trip_id() == trip.id

    def test_reads_are_unaffected_by_the_halt(self, conn: db.Connection, halt_file: Path) -> None:
        """§4.9: polling, AMBIGUOUS lookups and reconciliation continue while halted.

        Asserted by actually performing reads after the halt. This test used to
        assert only that the switch was halted, which proves nothing about reads.
        """
        from app.core import audit

        ks.trip(conn, "manual", halt_file=halt_file)
        switch = ks.load(conn, halt_file)
        assert switch.is_halted()

        assert audit.verify(conn).ok
        assert conn.execute("SELECT reason FROM trip").fetchone()["reason"] == "manual"
        assert switch.active_trip_id() is not None
        assert conn.execute("SELECT count(*) FROM killswitch_state").fetchone()[0] == 1

    def test_a_halt_does_not_block_a_re_read_of_its_own_state(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        """The executor must be able to learn *why* it is halted in order to stop."""
        ks.trip(conn, "clock skew 500s", halt_file=halt_file)
        assert "clock skew" in ks.load(conn, halt_file).reason_text()


# ---------------------------------------------------------------------------
# 3. Clearing needs two verified approvers, for the *active* trip
# ---------------------------------------------------------------------------
class TestClearingRequiresTwoApprovers:
    def test_two_distinct_approvers_clear_it(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        ks.clear(conn, trip.id, "fixed", clears(trip.id, "fixed"), halt_file=halt_file)
        assert not ks.load(conn, halt_file).is_halted()

    def test_one_approver_cannot_clear_it(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="2 distinct"):
            ks.clear(
                conn, trip.id, "fixed", clears(trip.id, "fixed", ("meera",)), halt_file=halt_file
            )
        assert ks.load(conn, halt_file).is_halted()

    def test_the_same_approver_twice_cannot_clear_it(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        """Two signatures from one person is one person."""
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="2 distinct"):
            ks.clear(
                conn,
                trip.id,
                "fixed",
                clears(trip.id, "fixed", ("meera", "meera")),
                halt_file=halt_file,
            )
        assert ks.load(conn, halt_file).is_halted()

    def test_a_reason_is_required(self, conn: db.Connection, halt_file: Path, roster: None) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="reason"):
            ks.clear(conn, trip.id, "   ", clears(trip.id, "x"), halt_file=halt_file)

    def test_each_clear_is_recorded_with_its_nonce(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        ks.clear(conn, trip.id, "fixed", clears(trip.id, "fixed"), halt_file=halt_file)
        rows = list(conn.execute("SELECT approver_id, challenge_nonce FROM trip_clear_signature"))
        assert len(rows) == 2
        assert len({row["challenge_nonce"] for row in rows}) == 2

    def test_clearing_removes_the_halt_file(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        assert halt_file.exists()
        ks.clear(conn, trip.id, "fixed", clears(trip.id, "fixed"), halt_file=halt_file)
        assert not halt_file.exists()


class TestClearingVerifiesSignatures:
    """§4.9: "two distinct roster approvers, each signing sha256(clear|trip|reason)".

    The first version counted distinct approver *strings* and never verified a
    signature, so two entries with no signature at all cleared the switch.
    """

    def test_an_unsigned_clear_is_refused(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        unsigned = [
            {"approver_id": "meera", "method": "HMAC_FALLBACK", "signed_via": "cli_hmac"},
            {"approver_id": "kabir", "method": "HMAC_FALLBACK", "signed_via": "cli_hmac"},
        ]
        with pytest.raises(ks.HaltedError, match="does not verify"):
            ks.clear(conn, trip.id, "no signature", unsigned, halt_file=halt_file)
        assert ks.load(conn, halt_file).is_halted()

    def test_an_empty_signature_is_refused(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        empty = [
            {"approver_id": "meera", "signature": b"", "challenge_nonce": "n1"},
            {"approver_id": "kabir", "signature": b"", "challenge_nonce": "n2"},
        ]
        with pytest.raises(ks.HaltedError, match="does not verify"):
            ks.clear(conn, trip.id, "empty", empty, halt_file=halt_file)

    def test_a_signature_over_a_different_reason_is_refused(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        """The reason is inside the signed payload, so it cannot be swapped."""
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        signed_for_another_reason = clears(trip.id, "a different reason")
        with pytest.raises(ks.HaltedError, match="does not verify"):
            ks.clear(
                conn, trip.id, "the real reason", signed_for_another_reason, halt_file=halt_file
            )

    def test_a_signature_over_a_different_trip_is_refused(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        signed_for_another = clears("some-other-trip-id", "fixed")
        with pytest.raises(ks.HaltedError):
            ks.clear(conn, trip.id, "fixed", signed_for_another, halt_file=halt_file)

    def test_another_approvers_signature_does_not_work(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "manual", halt_file=halt_file)
        forged = [
            ks.sign_clear(trip.id, "fixed", "meera"),
            ks.sign_clear(trip.id, "fixed", "priya"),
        ]
        forged[1].signature = forged[0].signature
        with pytest.raises(ks.HaltedError, match="does not verify"):
            ks.clear(conn, trip.id, "fixed", forged, halt_file=halt_file)


class TestClearingIsAtomic:
    """A clear that fails part-way must leave the switch exactly as it was.

    The first version wrote ``halted = 0`` in autocommit before inserting the
    signature rows. A failure in between left the switch reading RUNNING with the
    incident still open, and the code comment even invited a human to delete the
    now-stale HALT file — which would have completed the failure.
    """

    def _half_clear(self, conn: db.Connection, trip_id: str, reason: str, roster: None) -> None:
        """One valid clear plus one referencing an approver who does not exist."""
        bad = ks.ClearRequest(
            approver_id="ghost",
            signature=ks.sign_clear(trip_id, reason, "ghost").signature,
            nonce="n-ghost",
        )
        ks.clear(conn, trip_id, reason, [ks.sign_clear(trip_id, reason, "meera"), bad])

    def test_a_failed_clear_leaves_the_switch_halted(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "partial clear", halt_file=halt_file)
        with pytest.raises(Exception):  # noqa: B017 - the FK error is the point
            self._half_clear(conn, trip.id, "will fail midway", roster)

        assert ks.load(conn, halt_file).is_halted()

    def test_a_failed_clear_does_not_stamp_the_trip_cleared(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        trip = ks.trip(conn, "partial clear", halt_file=halt_file)
        with pytest.raises(Exception):  # noqa: B017
            self._half_clear(conn, trip.id, "will fail midway", roster)

        row = conn.execute("SELECT cleared_at FROM trip WHERE id = ?", (trip.id,)).fetchone()
        assert row["cleared_at"] is None

    def test_a_failed_clear_leaves_no_signature_rows(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        """No partial evidence: either both signatures are stored or neither is."""
        trip = ks.trip(conn, "partial clear", halt_file=halt_file)
        with pytest.raises(Exception):  # noqa: B017
            self._half_clear(conn, trip.id, "will fail midway", roster)

        assert conn.execute("SELECT count(*) FROM trip_clear_signature").fetchone()[0] == 0


class TestClearingRejectsAStaleTrip:
    """§4.9's real requirement is clearing *the* incident, not any incident.

    The first version accepted a caller-supplied trip_id and set ``halted = 0``
    unconditionally, so replaying an old, already-cleared trip's id waved through
    a newer incident that was still open.
    """

    def test_a_cleared_trip_id_cannot_clear_a_newer_trip(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        first = ks.trip(conn, "incident A", halt_file=halt_file)
        ks.clear(conn, first.id, "A done", clears(first.id, "A done"), halt_file=halt_file)

        second = ks.trip(conn, "incident B", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="not the active trip"):
            ks.clear(conn, first.id, "A done", clears(first.id, "A done"), halt_file=halt_file)

        assert ks.load(conn, halt_file).is_halted()
        row = conn.execute("SELECT cleared_at FROM trip WHERE id = ?", (second.id,)).fetchone()
        assert row["cleared_at"] is None, "incident B was cleared by a replayed id"

    def test_the_halt_file_survives_a_stale_clear_attempt(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        first = ks.trip(conn, "incident A", halt_file=halt_file)
        ks.clear(conn, first.id, "A done", clears(first.id, "A done"), halt_file=halt_file)
        ks.trip(conn, "incident B", halt_file=halt_file)

        with pytest.raises(ks.HaltedError):
            ks.clear(conn, first.id, "A done", clears(first.id, "A done"), halt_file=halt_file)

        assert halt_file.exists()

    def test_an_unknown_trip_id_is_refused(
        self, conn: db.Connection, halt_file: Path, roster: None
    ) -> None:
        ks.trip(conn, "real incident", halt_file=halt_file)
        with pytest.raises(ks.HaltedError, match="not the active trip"):
            ks.clear(
                conn, "made-up-id", "fixed", clears("made-up-id", "fixed"), halt_file=halt_file
            )


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

    def test_delimiters_prevent_a_field_split_collision(self) -> None:
        """("ab", "c") and ("a", "bc") must not produce the same preimage."""
        assert ks.clear_signature_payload("ab", "c") != ks.clear_signature_payload("a", "bc")


# ---------------------------------------------------------------------------
# 5. Automatic trip rules, §4.15 rows 24-29
# ---------------------------------------------------------------------------
#: The §4.15 rows 24-30 thresholds, as §4.17 writes them. Shared by reference so
#: an edit in one test class cannot silently move a threshold another asserts on.
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
        """A clock behind is just as wrong as one ahead."""
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
        "failure_type", ["ACCOUNT_UNDER_RESTRICTION", "TM_SUSPENDED", "CHANNEL_POLICY"]
    )
    def test_a_compliance_failure_trips_on_the_first(self, failure_type: str) -> None:
        reason = self.tripper().compliance(failure_type)
        assert reason and "r29" in reason

    def test_a_watchlist_reason_code_trips(self) -> None:
        assert (
            self.tripper().compliance("ACCOUNT_UNDER_RESTRICTION", ["WATCHLIST_SANCTIONS"])
            is not None
        )

    def test_a_bare_watchlist_failure_type_trips(self) -> None:
        assert self.tripper().compliance("WATCHLIST_ADVERSE_MEDIA") is not None

    def test_an_ordinary_failure_does_not_trip(self) -> None:
        assert self.tripper().compliance("ACCOUNT_CLOSED") is None

    def test_no_failure_type_does_not_trip(self) -> None:
        assert self.tripper().compliance(None) is None


class TestEvaluateRules:
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

    def test_evaluate_rules_ignores_compliance_when_no_failure_was_seen(self) -> None:
        """`None` means "nothing observed", which must not read as a failure."""
        assert ks.evaluate_rules(ks.AutomaticTripper(self.POLICY), failure_type=None) == []

    def test_evaluate_rules_still_judges_a_non_compliance_failure(self) -> None:
        assert (
            ks.evaluate_rules(ks.AutomaticTripper(self.POLICY), failure_type="ACCOUNT_CLOSED") == []
        )


# ---------------------------------------------------------------------------
# 6. Dangling trip id fails toward halted (D-B18)
# ---------------------------------------------------------------------------
class TestDanglingTripId:
    def test_a_trip_pointing_at_a_missing_row_still_halts(
        self, conn: db.Connection, halt_file: Path
    ) -> None:
        """The earlier version returned an empty Trip and left halted alone.

        That fails toward RUNNING, which is the wrong direction for this module.
        """
        ks.ensure_row(conn)
        conn.execute(
            "UPDATE killswitch_state SET halted = 1, trip_id = 'deleted-trip' WHERE id = 1"
        )

        record = ks.trip(conn, "recovery", halt_file=halt_file)

        row = conn.execute("SELECT halted, trip_id FROM killswitch_state WHERE id = 1").fetchone()
        assert row["halted"] == 1
        assert row["trip_id"] == record.id
        assert (
            conn.execute("SELECT count(*) FROM trip WHERE id = ?", (record.id,)).fetchone()[0] == 1
        )
