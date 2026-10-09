"""Thread safety, contention and lock-scope tests for the DB layer.

FINAL.md §5.3 (two processes, one SQLite file), §4.16 (a locked database halts
the executor), §4.8 (no transaction spans an API call).

These tests exist because measurement, not review, found the defects:

* a shared connection raised ``SQLite objects created in a thread can only be
  used in that same thread`` on **100%** of concurrent requests;
* there was no retry on ``database is locked``, so a single checkpoint fsync could
  surface as a failed payment;
* nothing asserted that a transaction is closed across an API boundary, so
  holding the single write lock during an HTTP call was possible by accident;
* ``Database.transaction()`` held no transaction at all, and left every row
  committed after an exception (D-B21).

A test asserting concurrency behaviour runs real threads against a real database
in ``tmp_path``. No mocks of the code under test (§10.1 rule 2).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.core import audit, db
from app.core import killswitch as ks


@pytest.fixture()
def database(tmp_path: Path) -> Iterator[db.Database]:
    database = db.Database(tmp_path / "app.sqlite")
    try:
        yield database
    finally:
        database.close()


def _write_audit(database: db.Database, worker: int, count: int) -> int:
    conn = database.connection()
    for index in range(count):
        audit.log_intent(conn, kind="T", payload={"worker": worker, "i": index})
    return count


class TestConnectionIsPerThread:
    """A connection belongs to the thread that made it. That is a hard SQLite rule."""

    def test_two_threads_get_two_connections(self, database: db.Database) -> None:
        seen: dict[str, int] = {}

        def capture() -> None:
            seen[threading.current_thread().name] = id(database.connection())

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: capture(), range(4)))

        assert len(seen) == 4
        assert len(set(seen.values())) == 4, "threads shared one connection"

    def test_one_thread_reuses_its_connection(self, database: db.Database) -> None:
        first = id(database.connection())
        assert id(database.connection()) == first

    def test_concurrent_writes_all_succeed(self, database: db.Database) -> None:
        """The defect this class exists to fix: 100% of writes used to fail."""
        with ThreadPoolExecutor(max_workers=4) as pool:
            written = list(pool.map(lambda w: _write_audit(database, w, 50), range(4)))

        assert sum(written) == 200
        count = database.execute("SELECT count(*) FROM audit_log").fetchone()[0]
        assert count == 200

    def test_concurrent_writes_produce_one_valid_chain(self, database: db.Database) -> None:
        """Four threads, one chain. Interleaving must not look like tampering.

        This is the property that matters most: a false positive on the audit
        chain halts the executor, so concurrency must not manufacture one.
        """
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda w: _write_audit(database, w, 40), range(4)))

        result = audit.verify(database.connection())
        assert result.ok, f"concurrent writes broke the chain: {result}"
        assert result.checked == 160

    def test_the_sequence_numbers_are_dense_and_unique(self, database: db.Database) -> None:
        """A gap in ``seq`` is exactly what verify() calls tampering."""
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda w: _write_audit(database, w, 25), range(4)))

        rows = database.execute("SELECT seq FROM audit_log ORDER BY seq")
        seqs = [row[0] for row in rows]
        assert seqs == list(range(1, 101))

    def test_close_releases_every_connection(self, tmp_path: Path) -> None:
        database = db.Database(tmp_path / "app.sqlite")

        def hold() -> None:
            database.connection()

        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda _: hold(), range(3)))
        database.close()
        with pytest.raises(RuntimeError, match="closed"):
            database.connection()

    def test_context_manager_closes(self, tmp_path: Path) -> None:
        with db.Database(tmp_path / "app.sqlite") as database:
            database.connection()
        with pytest.raises(RuntimeError, match="closed"):
            database.connection()


class TestReadersAreShared:
    def test_a_reader_can_be_used_from_another_thread(self, database: db.Database) -> None:
        """WAL readers never take the write lock, so sharing one is safe.

        This is the path a read-heavy dashboard takes: one connection, many
        threads, no lock contention.
        """
        database.connection()  # ensure the schema exists before reading
        conn = database.reader()
        result: list[int] = []

        def read() -> None:
            result.append(conn.execute("SELECT count(*) FROM user").fetchone()[0])

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: read(), range(4)))

        assert result == [0, 0, 0, 0]

    def test_the_shared_reader_physically_cannot_write(self, database: db.Database) -> None:
        """``query_only`` makes a stray write fail at SQLite, not silently race."""
        database.connection()
        with pytest.raises(sqlite3.OperationalError, match=r"readonly|query_only"):
            database.reader().execute("DELETE FROM user")


class TestContentionFailsSafe:
    """§4.16: a locked database halts the executor. It must not fail open."""

    def test_a_held_write_lock_is_retried_then_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "app.sqlite"
        # Both connections must be opened on the thread that will use them:
        # SQLite binds a connection to its creating thread, and using the blocker
        # from the main thread while the worker waits is exactly the mistake the
        # thread-safety tests above are about.
        holder = db.Database(path)
        blocker = db.Database(path)
        blocker_conn = blocker.connection()
        # Actually hold the write lock. Without BEGIN IMMEDIATE the statement
        # below commits immediately and there is nothing to contend with.
        blocker_conn.execute("BEGIN IMMEDIATE")
        blocker_conn.execute(
            "INSERT INTO run (id, started_at, shadow, state) VALUES ('x','t',0,'OPEN')"
        )

        blocked: list[BaseException] = []

        def retrying_write() -> None:
            try:
                db.with_retry(
                    lambda: holder.execute(
                        "INSERT INTO run (id, started_at, shadow, state) VALUES ('y','t',0,'OPEN')"
                    )
                )
            except BaseException as exc:
                blocked.append(exc)

        worker = threading.Thread(target=retrying_write)
        worker.start()
        # The lock is held for well under busy_timeout (5s), so a short pause is
        # enough to observe that the writer is genuinely waiting rather than
        # sailing through. Asserting "blocked" is the point of the test.
        time.sleep(0.5)
        assert worker.is_alive(), "the write did not block on the held lock"
        blocker_conn.execute("ROLLBACK")
        worker.join(timeout=15)

        assert not blocked, f"the write should have succeeded once the lock cleared: {blocked}"
        assert holder.execute("SELECT count(*) FROM run WHERE id='y'").fetchone()[0] == 1
        holder.close()
        blocker.close()

    def test_exhausted_retries_raise_database_busy(self, database: db.Database) -> None:
        """A permanent lock must surface as DatabaseBusyError, not a bare error.

        The distinction is load-bearing: §4.16 makes this a halt, and a caller
        that catches ``sqlite3.Error`` broadly would otherwise treat it as
        ignorable.
        """
        calls = {"n": 0}

        def always_locked() -> None:
            calls["n"] += 1
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(db.DatabaseBusyError, match="halt"):
            db.with_retry(always_locked, max_retries=2)
        assert calls["n"] == 3, "one attempt plus two retries"

    def test_non_lock_errors_are_not_retried(self, database: db.Database) -> None:
        """A constraint violation will not fix itself; retrying hides a real bug."""
        calls = {"n": 0}

        def unique_violation() -> None:
            calls["n"] += 1
            raise sqlite3.IntegrityError("UNIQUE constraint failed")

        with pytest.raises(sqlite3.IntegrityError):
            db.with_retry(unique_violation, max_retries=5)
        assert calls["n"] == 1, "a non-lock error was retried"

    def test_backoff_jitter_actually_varies(self) -> None:
        """Without jitter every waiter retries in lockstep and livelocks."""
        delays = {round(db._backoff_delay(3), 6) for _ in range(50)}
        assert len(delays) > 40, "backoff is not jittered"

    def test_backoff_is_bounded(self) -> None:
        for attempt in range(10):
            assert db._backoff_delay(attempt) <= db._MAX_BACKOFF_S

    def test_a_transaction_rolls_back_completely(self, database: db.Database) -> None:
        """Half a transaction is worse than none: a payment recorded without its
        audit entry, or the reverse.
        """
        conn = database.connection()
        with pytest.raises(RuntimeError), db.transaction(conn):
            conn.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('keep','t',0,'OPEN')"
            )
            audit.log_intent(conn, kind="X", payload={})
            raise RuntimeError("abort mid-transaction")

        assert conn.execute("SELECT count(*) FROM run WHERE id='keep'").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0

    def test_a_successful_transaction_commits_both(self, database: db.Database) -> None:
        conn = database.connection()
        with db.transaction(conn):
            conn.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('keep','t',0,'OPEN')"
            )
            audit.log_intent(conn, kind="X", payload={})

        assert conn.execute("SELECT count(*) FROM run WHERE id='keep'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 1


class TestDatabaseTransactionContext:
    """``Database.transaction()`` must behave exactly like ``db.transaction``.

    It did not (D-B21). The wrapper discarded the generator context manager, so
    CPython finalised it immediately: ``ROLLBACK`` ran before the caller's block
    even started, ``conn.in_transaction`` was ``False`` throughout, and an
    exception left every row committed. Both failures were silent because the
    writes succeeded.
    """

    def test_it_holds_the_lock_for_the_whole_block(self, database: db.Database) -> None:
        with database.transaction() as conn:
            assert conn.in_transaction, "the transaction never opened"

    def test_it_releases_the_lock_at_the_end(self, database: db.Database) -> None:
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('a','t',0,'OPEN')"
            )
        assert not database.connection().in_transaction, "the transaction outlived its block"

    def test_an_abort_rolls_everything_back(self, database: db.Database) -> None:
        conn = database.connection()
        with pytest.raises(RuntimeError), database.transaction() as block:
            block.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('b','t',0,'OPEN')"
            )
            block.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('c','t',0,'OPEN')"
            )
            raise RuntimeError("abort")

        assert conn.execute("SELECT count(*) FROM run WHERE id IN ('b','c')").fetchone()[0] == 0

    def test_the_lock_is_free_afterwards(self, database: db.Database) -> None:
        """The practical proof: another writer can write immediately after."""
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('a','t',0,'OPEN')"
            )

        other = db.connect(database.path)
        other.execute("INSERT INTO run (id, started_at, shadow, state) VALUES ('b','t',0,'OPEN')")
        assert other.execute("SELECT count(*) FROM run").fetchone()[0] == 2
        other.close()


class TestNoTransactionSpansAnApiCall:
    """§4.8: the write lock must be released before every Airwallex call.

    SQLite has one writer. A transaction held across an HTTP request would
    serialise every other writer behind that request's latency — a 20-second
    timeout would become a 20-second system-wide stall. The executor's ordering is
    what prevents it, and this is the test that keeps it honest.
    """

    def test_a_transaction_closes_at_the_end_of_its_block(self, database: db.Database) -> None:
        conn = database.connection()
        assert not db.in_transaction(conn)
        with db.transaction(conn):
            assert db.in_transaction(conn), "the transaction never opened"
        assert not db.in_transaction(conn), "the transaction outlived its block"

    def test_the_lock_is_free_after_the_transaction(self, database: db.Database) -> None:
        """The practical proof: another process can write immediately after."""
        conn = database.connection()
        other = db.connect(database.path)

        with db.transaction(conn):
            conn.execute(
                "INSERT INTO run (id, started_at, shadow, state) VALUES ('a','t',0,'OPEN')"
            )

        # Would raise DatabaseBusyError if the lock were still held.
        other.execute("INSERT INTO run (id, started_at, shadow, state) VALUES ('b','t',0,'OPEN')")
        assert other.execute("SELECT count(*) FROM run").fetchone()[0] == 2
        other.close()

    def test_the_guard_fires_when_the_lock_is_held(self, database: db.Database) -> None:
        """``assert_no_write_lock`` is what makes §4.8 checkable, not aspirational.

        The executor calls this immediately before every Airwallex request. If the
        guard ever stops working the executor would silently hold the single write
        lock across a 20-second HTTP call and stall the whole system, so this
        asserts the guard still has teeth.
        """
        conn = database.connection()
        with pytest.raises(db.StaleSnapshotError, match=r"4\.8"), db.transaction(conn):
            db.assert_no_write_lock(conn, doing="call Airwallex")

    def test_the_guard_is_quiet_when_nothing_is_held(self, database: db.Database) -> None:
        conn = database.connection()
        db.assert_no_write_lock(conn, doing="call Airwallex")


class TestMigrationIsConcurrencySafe:
    """Two threads or two processes opening a brand-new file must not race."""

    def test_concurrent_first_connections_do_not_collide(self, tmp_path: Path) -> None:
        database = db.Database(tmp_path / "fresh.sqlite")
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                versions = list(
                    pool.map(lambda _: db.user_version(database.connection()), range(4))
                )
            assert versions == [db.SCHEMA_VERSION] * 4
        finally:
            database.close()

    def test_a_stale_lock_file_does_not_wedge_startup(self, tmp_path: Path) -> None:
        """A lock left by a ``kill -9`` must be reclaimed, not waited out.

        The lock file used to have one fixed name, so a stale one blocked every
        database on the machine for the full 30 s timeout (D-B21).
        """
        path = tmp_path / "stale.sqlite"
        lock = db._migrate_lock_path(path)
        lock.write_text("999999", encoding="utf-8")
        # Backdate it past the timeout so it reads as abandoned.
        import os
        import time as _time

        os.utime(lock, (0, 0))

        started = _time.monotonic()
        conn = db.connect(path)
        try:
            assert db.user_version(conn) == db.SCHEMA_VERSION
        finally:
            conn.close()
        assert _time.monotonic() - started < db.MIGRATE_TIMEOUT_S
        assert not lock.exists()


class TestKillSwitchUnderContention:
    """§4.9 tripping twice concurrently must still produce one trip."""

    def test_concurrent_trips_produce_exactly_one_trip(self, database: db.Database) -> None:
        outcomes: list[object] = []

        def trip_once() -> None:
            try:
                outcomes.append(ks.trip(database.connection(), "race", origin="test"))
            except BaseException as exc:
                outcomes.append(exc)

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: trip_once(), range(4)))

        assert not [o for o in outcomes if isinstance(o, BaseException)], (
            f"a concurrent trip raised: {[o for o in outcomes if isinstance(o, BaseException)]}"
        )
        assert database.execute("SELECT count(*) FROM trip").fetchone()[0] == 1

    def test_every_id_handed_back_is_the_clearable_one(self, database: db.Database) -> None:
        """An operator who trips, reads the id and clears it must not be refused.

        Before the fix, four concurrent trips produced six ``Trip`` objects with
        six ids while only one was the active trip, so five of the six ids the
        system returned could never be cleared — the switch was stuck in HALTED
        with no in-band way out (D-B21).
        """
        returned: list[object] = []

        def trip_once() -> None:
            returned.append(ks.trip(database.connection(), "race", origin="test"))

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: trip_once(), range(4)))

        returned_ids = {t.id for t in returned if isinstance(t, ks.Trip)}
        active = database.execute("SELECT trip_id FROM killswitch_state WHERE id=1").fetchone()[0]
        assert returned_ids == {active}

    def test_the_trip_is_audited(self, database: db.Database) -> None:
        """The audit entry must be in the same transaction as the halt.

        It was not: forcing the append to fail left the switch engaged with a trip
        row and a reason and **zero** rows in the append-only log, and
        ``verify()`` reported ``ok=True, checked=0`` (D-B21).
        """
        conn = database.connection()
        ks.trip(conn, "audited trip", origin="test")

        rows = conn.execute(
            "SELECT payload_json FROM audit_log WHERE kind = 'KILLSWITCH_TRIP'"
        ).fetchall()
        assert len(rows) == 1
        assert "audited trip" in rows[0]["payload_json"]
        assert audit.verify(conn).ok

    def test_the_switch_is_halted_after_a_race(self, database: db.Database) -> None:
        def trip_once() -> None:
            ks.trip(database.connection(), "race", origin="test")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: trip_once(), range(4)))

        switch = ks.load(database.connection(), database.path.parent / "HALT")
        assert switch.is_halted()
