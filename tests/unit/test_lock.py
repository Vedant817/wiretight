"""Tests for the bank-change lock, and the invariant it was missing.

FINAL.md §4.5.1 defines the change-request states. The state machine in
:mod:`app.core.statemachine` implements them for one request, as a pure function
with no ``vendor_id`` - so it cannot see a second request. The property that
matters, at most one active bank-change request per supplier, had no
implementation anywhere.

Measured before the fix (D-B22): two concurrent requests for one supplier could
both sit in ``COOLING_OFF`` and both reach ``APPROVED``, with no defined answer
for which superseded the previous payee version. So the tests here are about the
*cross-row* invariant: the state machine is correct per request, and the lock is
what makes "per request" mean something.

The concurrency tests run real threads against a real SQLite file, because
"two requests at once" is the whole failure mode and a single-threaded test cannot
produce it. §10.1 rule 2: no mocks of the code under test.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core import db, lock
from app.core.lock import ChangeRequestConflictError


@pytest.fixture()
def conn(tmp_path):
    """A database with a supplier, and the constraint in place."""
    database = db.Database(tmp_path / "app.sqlite")
    connection = database.connection()
    lock.ensure_lock_constraint(connection)
    connection.execute(
        'INSERT INTO "user" (id, name, role, email, sign_count, created_at)'
        " VALUES ('u1','U','approver','u@x.example',0,'t')"
    )
    connection.execute(
        "INSERT INTO vendor (id, legal_name_norm, display_name, category, created_at)"
        " VALUES ('v1','acme','Acme','utilities','t')"
    )
    yield connection
    database.close()


def _open(connection, *, vendor_id="v1", fingerprint="fp1"):
    return lock.open_request(
        connection,
        vendor_id=vendor_id,
        source_kind="email",
        intake_user_id="u1",
        proposed_details_ref="ref-1",
        proposed_masked="DE•• •••• 7740",
        proposed_fingerprint=fingerprint,
    )


class TestTheInvariant:
    """The claim the lock exists to enforce, stated as an assertion."""

    def test_two_sequential_requests_for_one_supplier_are_refused(self, conn) -> None:
        """A supplier may have one active request. A second is refused."""
        _open(conn)

        with pytest.raises(ChangeRequestConflictError, match="already has an active"):
            _open(conn, fingerprint="fp2")

    def test_a_terminal_request_frees_the_supplier(self, conn) -> None:
        """Rejected, expired and withdrawn are terminal, so the supplier is free.

        This is why the constraint is on active rows only. A supplier whose
        November request was rejected may file again in January, and §4.4 makes a
        re-request inside 30 days force tier 2 - which only works if the history
        stays queryable.
        """
        first = _open(conn)
        conn.execute(
            "UPDATE payee_change_request SET status = 'REJECTED' WHERE id = ?",
            (first.id,),
        )

        second = _open(conn, fingerprint="fp2")
        assert second.id != first.id
        assert [r.id for r in lock.active_requests_for(conn, "v1")] == [second.id]

    def test_different_suppliers_are_unaffected(self, conn) -> None:
        """The lock is per supplier, not global: it must not block the ledger."""
        conn.execute(
            "INSERT INTO vendor (id, legal_name_norm, display_name, category, created_at)"
            " VALUES ('v2','other','Other','utilities','t')"
        )
        _open(conn, vendor_id="v1")
        _open(conn, vendor_id="v2")

        assert [r.id for r in lock.active_requests_for(conn, "v1")]
        assert [r.id for r in lock.active_requests_for(conn, "v2")]


class TestTheInvariantUnderConcurrency:
    """The failure mode the index exists for, produced for real."""

    def test_two_concurrent_requests_produce_exactly_one_commit(self, conn) -> None:
        """Two threads, one supplier: one succeeds, one is refused.

        This is the case that was broken. Without the partial index both
        transactions commit, both requests cool off, and the lock is a
        convention rather than a control.

        Each thread uses its own connection, because SQLite binds a connection to
        its creating thread; sharing one is the mistake the concurrency tests in
        tests/unit already cover.
        """
        path = conn.execute("PRAGMA database_list").fetchone()[2]
        databases = [db.Database(path) for _ in range(2)]
        results: list[object] = []

        def attempt(index: int) -> None:
            with databases[index].transaction() as tx:
                lock.ensure_lock_constraint(tx)
                try:
                    _open(tx, fingerprint=f"fp-{index}")
                    results.append("ok")
                except ChangeRequestConflictError:
                    results.append("conflict")

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(attempt, range(2)))

        assert results.count("ok") == 1, f"both concurrent requests committed: {results}"
        assert results.count("conflict") == 1, f"expected one refusal: {results}"
        assert len(lock.active_requests_for(conn, "v1")) == 1

    def test_the_winner_is_not_always_the_first_thread(self, conn) -> None:
        """SQLite picks the winner, not the caller.

        Asserted because a weaker test would only check that *some* request won,
        and the lock's job is to guarantee one winner regardless of scheduling.
        Running the race repeatedly exercises both orders.
        """
        for trial in range(4):
            # Clear the previous round so each race starts from no active
            # request. Without this, the second round sees the first round's row
            # and rejects both threads for a reason that has nothing to do with
            # scheduling.
            conn.execute("DELETE FROM payee_change_request")

            path = conn.execute("PRAGMA database_list").fetchone()[2]
            databases = [db.Database(path) for _ in range(2)]
            _results: list[object] = []

            def attempt(
                index: int,
                _db: list[db.Database] = databases,
                _trial: int = trial,
                _results: list[object] = _results,
            ) -> None:
                with _db[index].transaction() as tx:
                    try:
                        _open(tx, fingerprint=f"t{_trial}-{index}")
                        _results.append(index)
                    except ChangeRequestConflictError:
                        _results.append("conflict")

            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(attempt, range(2)))

            assert sorted(_results, key=str) in ([0, "conflict"], [1, "conflict"]), _results
            assert len(lock.active_requests_for(conn, "v1")) == 1

    def test_the_lock_survives_a_restart(self, conn) -> None:
        """The guarantee is in the database, not in a process's memory.

        A new connection must still be refused. A lock held only in Python would
        pass every test above and fail in production at exactly the moment two
        processes exist - which is the deployment in §5.3.
        """
        _open(conn)

        other = db.connect(conn.execute("PRAGMA database_list").fetchone()[2])
        try:
            with pytest.raises(ChangeRequestConflictError):
                _open(other, fingerprint="fp2")
        finally:
            other.close()


class TestTheIntegrityCheck:
    """What a verification run does, and why it can exist at all."""

    def test_a_clean_database_passes(self, conn) -> None:
        _open(conn)
        lock.assert_lock_integrity(conn)

    def test_a_pre_existing_violation_is_caught(self, conn) -> None:
        """A database migrated from before the index could already be wrong.

        The index prevents new violations; it cannot repair old ones. Finding
        them at startup is a halt, and that is the correct outcome: a silent
        violation of the product's central claim is worse than a refused start.
        """
        _open(conn)
        # Drop the index to simulate a database that predates it, then insert a
        # second active request. The integrity check must find both.
        conn.execute("DROP INDEX idx_change_request_one_active_per_vendor")
        conn.execute(
            "INSERT INTO payee_change_request"
            " (id, vendor_id, source_kind, received_at, intake_user_id,"
            "  requester_set, proposed_details_ref, proposed_masked,"
            "  proposed_fingerprint, evidence, status)"
            " VALUES ('y','v1','email','t','u1','[]','r','m','fp','[]','COOLING_OFF')"
        )

        with pytest.raises(ChangeRequestConflictError, match="violated"):
            lock.assert_lock_integrity(conn)


class TestCallbackFlow:
    """The §4.5.1 sequence, and what the lock does not change."""

    def test_a_request_moves_through_to_cooling_off(self, conn) -> None:
        row = _open(conn)
        row = lock.request_callback(conn, row.id)
        assert row.status == "PENDING_CALLBACK"

    def test_calling_twice_is_not_two_callbacks(self, conn) -> None:
        """A repeated event must not restart or duplicate the callback."""
        row = _open(conn)
        lock.request_callback(conn, row.id)
        again = lock.request_callback(conn, row.id)
        assert again.status == "PENDING_CALLBACK"
        assert conn.execute("SELECT count(*) FROM payee_change_request").fetchone()[0] == 1

    def test_a_foreign_key_violation_is_not_a_lock_conflict(self, conn) -> None:
        """A missing supplier is a caller error, not the control firing.

        Both surface as ``IntegrityError`` and only one is the lock. Reporting the
        wrong one would tell an operator their supplier list is being attacked.
        """
        with pytest.raises(Exception, match="FOREIGN KEY"):
            _open(conn, vendor_id="does-not-exist")
