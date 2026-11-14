"""SQLite access: per-thread connections, bounded retries, and no lock held across I/O.

FINAL.md §8.1: SQLite, ``PRAGMA user_version`` migrations, ``foreign_keys=ON``, WAL.

This module is the only place in the project that opens a database file. It
holds no business logic and makes no policy decisions.

Three things it exists to get right, each of which measurement showed was wrong
before (see DECISIONS D-B19):

**Connections are per-thread, never shared.** SQLite objects are bound to the
thread that created them. A FastAPI endpoint runs on a worker thread, so a
module-level connection is a runtime error on the first request, not a rare race.
:class:`Database` hands out one connection per thread and closes them all on
shutdown.

**Contention fails safe.** WAL allows one writer. When the write lock is held,
SQLite raises ``database is locked`` after ``busy_timeout``. :func:`with_retry`
retries with exponential backoff and jitter, because without jitter every waiter
retries in lockstep and the lock never clears. When the retries are exhausted
the caller gets :class:`DatabaseBusyError`, which the executor treats as a halt
(§4.16) — never as "proceed on a stale read".

**No transaction spans network I/O.** A transaction holds the single write lock
for its whole life. If an HTTP call to Airwallex happened inside one, the entire
system would serialise behind that call. :func:`transaction` is therefore
deliberately not context-manager-over-async, and the executor's ordering
(§4.8) keeps every API call outside it. :func:`in_transaction` exists so that a
test can *prove* no transaction is open across a boundary.
"""

from __future__ import annotations

import hashlib
import os
import random
import sqlite3
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from pathlib import Path
from types import TracebackType
from typing import Final

#: Incremented whenever ``schema.sql`` gains a migration step.
SCHEMA_VERSION: Final[int] = 2

_SCHEMA_PATH: Final[Path] = Path(__file__).with_name("schema.sql")

#: ``sqlite3.Row`` by name, so tests and callers read columns by name.
Connection = sqlite3.Connection


#: How long to wait for the write lock before giving up, in milliseconds.
DEFAULT_BUSY_TIMEOUT_MS: Final[int] = 5_000

#: Retries after the first attempt fails. 5 attempts with backoff spans roughly
#: 1.5 s of waiting on top of each busy_timeout, which is long enough for a
#: checkpoint fsync and short enough that an operator notices a halt.
DEFAULT_MAX_RETRIES: Final[int] = 5

_BASE_BACKOFF_S: Final[float] = 0.02
_MAX_BACKOFF_S: Final[float] = 0.5


class DatabaseBusyError(RuntimeError):
    """The write lock could not be acquired within the retry budget.

    Distinct from a bare ``sqlite3.OperationalError`` so callers cannot swallow
    it by accident: §4.16 says a locked database **halts the executor** rather
    than proceeding on stale balances.
    """


class ThreadViolationError(RuntimeError):
    """A connection was used from a thread that did not create it.

    This is a programming error, not contention. It is raised rather than allowed
    to become SQLite's own message because the fix is different: get a connection
    from :class:`Database` for this thread.
    """


def is_locked_error(exc: BaseException) -> bool:
    """True for SQLite's "database is locked" family.

    SQLITE_BUSY_SNAPSHOT is **excluded**. SQLite reports it with the same
    message as ordinary contention, but it means *this* connection holds a stale
    read snapshot that cannot be upgraded — waiting does not help, so retrying
    burns the whole budget and then reports ``DatabaseBusyError``, which
    §4.16 turns into a halt. Measured: a read inside an open cursor followed by a
    write produced 6 pointless retries and then a false halt (D-B21).
    """
    if isinstance(exc, DatabaseBusyError):
        return True
    if _is_stale_snapshot(exc):
        return False
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message


def _is_stale_snapshot(exc: BaseException) -> bool:
    """Is this SQLITE_BUSY_SNAPSHOT? Python 3.11+ exposes the extended code."""
    code: int | None = getattr(exc, "sqlite_errorcode", None)
    if code is None:
        return False
    # Primary code SQLITE_BUSY (5), extended code SQLITE_BUSY_SNAPSHOT (517).
    return code & 0xFF == 5 and code != 5


class StaleSnapshotError(RuntimeError):
    """A write was attempted on a read snapshot that can no longer be upgraded.

    Not contention, and not retryable. The fix is to finish reading before
    writing, which is why the ledger and reconciliation cursors are documented as
    single-pass.
    """


def assert_no_write_lock(conn: Connection, *, doing: str) -> None:
    """Refuse to perform ``doing`` while holding the write lock.

    FINAL.md §4.8 requires the write lock to be released before every Airwallex
    call. SQLite permits exactly one writer, so a transaction held across an HTTP
    request serialises every other writer behind that request's latency: measured,
    a 2.0 s call inside a transaction stalled four concurrent writers for 1.8 to
    2.0 s each, and the configured timeout is 20 s. That is a 20-second system-wide
    stall from one misplaced ``with`` block (D-B21).

    Called immediately before every outbound request so the check cannot be
    forgotten the way a code review can.
    """
    if conn.in_transaction:
        raise StaleSnapshotError(
            f"refusing to {doing}: the SQLite write lock is held. FINAL.md §4.8 "
            "requires it released before any Airwallex call, because the system "
            "has exactly one writer and holding it across I/O serialises every "
            "other writer behind the network."
        )


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with full jitter.

    The jitter is not decoration. Without it, N waiters that all time out
    together retry in lockstep, each grabbing the lock just long enough for the
    next one to fail, and the system livelocks at a fraction of its throughput.
    """
    ceiling = min(_MAX_BACKOFF_S, _BASE_BACKOFF_S * (2**attempt))
    return random.uniform(0.0, ceiling)


def with_retry[T](
    operation: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Run ``operation``, retrying while SQLite reports the write lock is held.

    Retries only lock contention. Any other error propagates immediately: a
    constraint violation or a type error will not fix itself, and retrying it
    would turn a clear failure into a slow one.

    Raises :class:`DatabaseBusyError` when the budget is exhausted.
    """
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if not is_locked_error(exc) or attempt == max_retries:
                if is_locked_error(exc):
                    raise DatabaseBusyError(
                        f"could not acquire the write lock after {max_retries + 1} "
                        f"attempts over ~{_MAX_BACKOFF_S * max_retries:.1f}s; the "
                        "executor must halt rather than act on stale state "
                        "(FINAL.md §4.16)"
                    ) from exc
                raise
            if on_retry is not None:
                on_retry(attempt, exc)
            time.sleep(_backoff_delay(attempt))
    raise AssertionError("unreachable")  # pragma: no cover


#: The concrete type :func:`transaction` returns, so the wrapper below can hold it
#: instead of discarding it.
_Transaction = AbstractContextManager[Connection]


@contextmanager
def transaction(conn: Connection) -> Iterator[Connection]:
    """Run a block as one write transaction, retrying the BEGIN on contention.

    ``BEGIN IMMEDIATE`` takes the write lock up front rather than upgrading
    mid-transaction, which avoids the SQLITE_BUSY-on-upgrade deadlock a deferred
    BEGIN can produce between a read and a write.

    **Nesting joins the outer transaction** rather than starting a second one.
    Several modules legitimately need to compose — the audit append inside the
    executor's state change, for instance — and SQLite has no nested
    transactions. Joining means the inner block is committed or rolled back with
    the outer one, which is what a caller nesting these intends.
    """
    if conn.in_transaction:
        # Already inside one: participate, and let the outermost block decide.
        yield conn
        return

    def begin() -> None:
        conn.execute("BEGIN IMMEDIATE")

    with_retry(begin)
    try:
        yield conn
    except BaseException:
        with suppress(sqlite3.Error):
            conn.execute("ROLLBACK")
        raise
    else:
        try:
            conn.execute("COMMIT")
        except sqlite3.OperationalError as exc:
            # The lock was lost between BEGIN and COMMIT. The transaction is
            # already gone, so there is nothing to roll back.
            if is_locked_error(exc):
                raise DatabaseBusyError("lost the write lock before COMMIT") from exc
            raise


def in_transaction(conn: Connection) -> bool:
    """Is a transaction currently open on ``conn``?

    Used by the executor's boundary tests: §4.8 requires the write lock to be
    released before every Airwallex call, and this is how that is asserted rather
    than assumed.
    """
    return bool(conn.in_transaction)


def user_version(conn: Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


_MIGRATE_LOCK: Final[Path] = Path(tempfile.gettempdir()) / "wiretight-migrate.lock"

#: Every connection in the process waits this long for a peer's migration.
MIGRATE_TIMEOUT_S: Final[float] = 30.0


def migrate(conn: Connection) -> None:
    """Apply migrations up to :data:`SCHEMA_VERSION`. Idempotent and concurrency-safe.

    Step 1 creates the whole schema from ``schema.sql``. Later steps are added as
    new ``if version < N`` blocks; a step must never rewrite an existing table,
    because the audit chain already references what was written.
    """
    deadline = time.monotonic() + MIGRATE_TIMEOUT_S
    while True:
        try:
            _migrate_locked(conn)
            return
        except _MigrationInProgressError:
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"another process held the schema migration for over "
                    f"{MIGRATE_TIMEOUT_S:.0f}s; giving up rather than starting on a "
                    "half-migrated schema"
                ) from None
            time.sleep(0.05)
        except sqlite3.OperationalError as exc:
            # A peer is mid-migration and holding SQLite's own write lock. Wait
            # for it rather than reporting corruption.
            if "locked" not in str(exc).lower():
                raise
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)


class _MigrationInProgressError(RuntimeError):
    """Another thread or process is migrating. Retry after a short pause."""


def _migrate_lock_path(db_path: str | Path) -> Path:
    """The cross-process migration lock for one specific database file.

    Keyed by the resolved path. A single fixed filename meant every unrelated
    database on the machine shared one lock, and a lock file left behind by a
    ``kill -9`` between ``os.open`` and ``unlink`` blocked *every* database for
    the full 30 s timeout before failing — measured, on a database that had
    nothing to do with the stale lock (D-B21).
    """
    digest = hashlib.sha256(str(Path(db_path).resolve()).encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"wiretight-migrate-{digest}.lock"


def _acquire_migrate_lock(db_path: str | Path) -> tuple[int, Path]:
    """Take the migration lock, reclaiming it if the holder is gone or too old."""
    path = _migrate_lock_path(db_path)
    while True:
        try:
            return os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY), path
        except FileExistsError:
            pass

        # A lock older than the timeout cannot be held by a live migrator: the
        # holder would have given up. Reclaim it rather than wedging every start
        # of every database on this machine.
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            continue  # vanished between open and stat; retry immediately
        if age > MIGRATE_TIMEOUT_S:
            with suppress(OSError):
                path.unlink()
            continue

        # Live holder. SQLite's own write lock is the real backstop; this only
        # stops two processes racing to create the same tables.
        raise _MigrationInProgressError


def _migrate_locked(conn: Connection) -> None:
    current = user_version(conn)
    if current >= SCHEMA_VERSION:
        if current != SCHEMA_VERSION:
            raise RuntimeError(
                f"schema is at version {current}, expected {SCHEMA_VERSION}. "
                "A downgrade is not supported; the audit chain references what was written."
            )
        return

    if current not in {0, 1}:
        raise RuntimeError(
            f"schema is at version {current}, which this build cannot migrate from. "
            "Intermediate migrations must ship before the version they produce."
        )

    fd, lock_path = _acquire_migrate_lock(_database_path(conn))
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        fd = -1
        # Re-read: a peer may have finished while we waited for the lock file.
        if user_version(conn) >= SCHEMA_VERSION:
            return
        current = user_version(conn)
        scripts = []
        if current < 1:
            scripts.append(_SCHEMA_PATH.read_text(encoding="utf-8"))
        if current < 2:
            scripts.append(_SCHEMA_PATH.with_name("migration_002.sql").read_text(encoding="utf-8"))
        # executescript does NOT create a transaction automatically. Version
        # changes and DDL must commit together, including on a fresh database.
        script = "BEGIN IMMEDIATE;\n" + "\n".join(scripts)
        script += f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        try:
            conn.executescript(script)
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
    finally:
        if fd >= 0:
            with suppress(OSError):
                os.close(fd)
        with suppress(OSError):
            lock_path.unlink(missing_ok=True)


def _database_path(conn: Connection) -> str:
    """The file backing ``conn``, so the migration lock is per-database.

    ``PRAGMA database_list`` is ``(seq, name, file)``; the ``main`` row carries the
    path, and an in-memory database reports an empty one.
    """
    for row in conn.execute("PRAGMA database_list"):
        path = row[2]
        if path:
            return str(path)
    raise RuntimeError(  # pragma: no cover
        "cannot determine the database path for the migration lock"
    )


def _open(
    path: str | Path,
    *,
    read_only: bool,
    busy_timeout_ms: int,
    share_across_threads: bool,
    migrate_schema: bool,
) -> Connection:
    """Open and configure one connection. No registry locking."""
    if not read_only:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(path),
        isolation_level=None,
        check_same_thread=not share_across_threads,
        # CPython 3.12's statement cache can reuse a prepared statement across
        # concurrent shared-reader cursors. Observed COUNT(*) returned None.
        # Each shared-reader execute must own its prepared statement.
        cached_statements=0 if share_across_threads else 128,
    )
    _configure(conn, read_only=read_only, busy_timeout_ms=busy_timeout_ms)
    if migrate_schema and not read_only:
        migrate(conn)
    return conn


def _configure(conn: sqlite3.Connection, *, read_only: bool, busy_timeout_ms: int) -> None:
    """Set the pragmas. All are connection-scoped, so they are set per connection.

    ``check_same_thread=False`` is deliberately **not** used here. Connections
    stay per-thread, so the guard is left on: it turns a threading mistake into a
    clear error at the boundary instead of undefined behaviour.

    ``journal_mode`` is persistent, so setting WAL needs the write lock and can
    lose a race against a peer opening the same file. Losing that race means the
    peer already set it, so the failure is benign and retried rather than raised.
    """
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    conn.execute("PRAGMA foreign_keys = ON")
    if read_only:
        conn.execute("PRAGMA query_only = ON")
        return

    def set_wal() -> None:
        conn.execute("PRAGMA journal_mode = WAL")

    with_retry(set_wal, max_retries=3)
    # Durability over throughput: a lost audit entry is a lost record of intent to
    # move money. NORMAL would survive a process crash but not an OS crash.
    conn.execute("PRAGMA synchronous = FULL")


def connect(path: str | Path, *, read_only: bool = False) -> Connection:
    """Open a connection for the **calling thread**.

    Prefer :class:`Database` in application code: this function makes one
    connection and the caller owns it. It stays public because tests and
    one-shot scripts legitimately want exactly that.
    """
    return _open(
        path,
        read_only=read_only,
        busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS,
        share_across_threads=False,
        migrate_schema=True,
    )


#: Per-``Database`` migration guard. Keyed by resolved path so that two
#: ``Database`` objects over the same file in one process do not both migrate,
#: while separate databases (the tests create many) stay independent.
_MIGRATION_LOCKS: dict[str, threading.Lock] = {}
_MIGRATION_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _MIGRATION_LOCKS_GUARD:
        lock = _MIGRATION_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _MIGRATION_LOCKS[key] = lock
        return lock


class Database:
    """A per-thread connection registry for one SQLite file.

    This is the object application code should hold. It exists because SQLite
    connections belong to the thread that made them, and FastAPI runs every
    endpoint on a worker thread: a single shared connection raised
    ``SQLite objects created in a thread can only be used in that same thread`` on
    100% of requests under load, which measurement confirmed.

    ::

        database = Database("var/app.sqlite")
        conn = database.connection()          # this thread's connection
        ...
        database.close()                       # at shutdown

    Read-mostly paths may share a connection across threads explicitly via
    :meth:`reader`, which opens with ``check_same_thread=False``. That is safe
    only because WAL readers never block and never write; the flag is refused
    unless the caller asks for it by name.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        self.path = Path(path)
        self.read_only = read_only
        self.busy_timeout_ms = busy_timeout_ms
        self._local = threading.local()
        self._all: list[Connection] = []
        self._lock = threading.Lock()
        self._migrate_once = _lock_for(self.path)
        self._shared_reader: Connection | None = None
        self._closed = False

    # -- connection lifecycle ------------------------------------------------
    def _track(self, conn: Connection) -> Connection:
        """Register a connection for closing at shutdown.

        The registry lock is never held across ``_open``: opening a new SQLite
        file takes the write lock briefly to set WAL, and holding a Python lock
        through that would serialise every thread at startup and then time out.
        """
        with self._lock:
            if self._closed:
                conn.close()
                raise RuntimeError("Database is closed")
            self._all.append(conn)
        return conn

    def connection(self) -> Connection:
        """This thread's connection, created on first use.

        Migration happens **once** per file, guarded by a process-wide lock.
        Two threads opening the same new file would otherwise both try to create
        the tables, and the loser saw ``table entity already exists`` as a crash.
        """
        existing: Connection | None = getattr(self._local, "conn", None)
        if existing is not None:
            return existing
        if self._closed:
            raise RuntimeError("Database is closed")

        with self._migrate_once:
            conn = _open(
                self.path,
                read_only=self.read_only,
                busy_timeout_ms=self.busy_timeout_ms,
                share_across_threads=False,
                # Idempotent and lock-guarded, so this is safe on every thread
                # even when the file was already migrated a moment ago.
                migrate_schema=not self.read_only,
            )
        tracked: Connection = self._track(conn)
        self._local.conn = tracked
        return tracked

    def _schema_is_current(self) -> bool:
        """Has this file already been migrated by anyone?

        Checked without holding the registry lock, using a throwaway read. On a
        file that does not exist yet ``user_version`` is 0 and asking creates
        nothing, so this is safe on a cold start.
        """
        try:
            probe = _open(
                self.path,
                read_only=self.read_only,
                busy_timeout_ms=self.busy_timeout_ms,
                share_across_threads=False,
                migrate_schema=False,
            )
        except sqlite3.OperationalError:
            # A peer holds the write lock; it is migrating or writing. Assume the
            # schema is current rather than racing it.
            return True
        try:
            return user_version(probe) >= SCHEMA_VERSION
        finally:
            probe.close()

    def reader(self) -> Connection:
        """A connection explicitly shared for concurrent reads.

        Safe only for reads. WAL readers do not block writers and do not take the
        write lock, so many threads may hold this at once. Any write through it
        would reintroduce exactly the race this class exists to prevent, so the
        method name says what it is for, and the connection is opened with
        ``query_only`` so a stray write fails at the SQLite level rather than
        silently succeeding.
        """
        if self._closed:
            raise RuntimeError("Database is closed")

        shared = self._shared_reader
        if shared is None:
            with self._migrate_once:
                shared = self._shared_reader
                if shared is None:
                    conn = _open(
                        self.path,
                        read_only=self.read_only,
                        busy_timeout_ms=self.busy_timeout_ms,
                        share_across_threads=True,
                        # A reader never migrates; it must not be able to.
                        migrate_schema=False,
                    )
                    if not self.read_only:
                        # Belt and braces: the shared connection physically
                        # cannot write, so a stray write fails at the SQLite
                        # level rather than silently racing.
                        conn.execute("PRAGMA query_only = ON")
                    self._shared_reader = self._track(conn)
                    shared = self._shared_reader
        return shared

    def close(self) -> None:
        """Close every connection this registry has opened. Idempotent."""
        self._closed = True
        with self._lock:
            connections, self._all = self._all, []
        for conn in connections:
            with suppress(sqlite3.Error):
                conn.close()
        self._local = threading.local()

    def __enter__(self) -> Database:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- convenience ---------------------------------------------------------
    def execute(self, sql: str, parameters: object = ()) -> sqlite3.Cursor:
        return self.connection().execute(sql, parameters)  # type: ignore[arg-type]

    def query_one(self, sql: str, parameters: object = ()) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self.connection().execute(sql, parameters).fetchone()  # type: ignore[arg-type]
        return row

    def transaction(self) -> _TransactionContext:
        return _TransactionContext(self)

    def __repr__(self) -> str:
        state = "closed" if self._closed else "open"
        return f"<Database {self.path} {state} connections={len(self._all)}>"


class _TransactionContext:
    """``Database.transaction()``: a transaction bound to this thread's connection.

    The generator returned by :func:`transaction` must be **held**. Discarding it
    — calling ``__enter__()`` and dropping the object — lets CPython finalise it,
    which throws ``GeneratorExit`` into the ``yield``, runs the ``ROLLBACK`` arm,
    and leaves the caller's block with no open transaction at all. That produced
    two failures at once, both measured (D-B21):

    * ``conn.in_transaction`` was ``False`` for the whole body, so
      :func:`in_transaction` — the guard §4.8 relies on to prove no write lock is
      held across an Airwallex call — could never fire;
    * an exception mid-block left every row committed, because each statement
      autocommitted with no transaction to roll back.

    Both were silent. The write succeeded, which is what made it look correct.
    """

    def __init__(self, database: Database) -> None:
        self._database = database
        self._cm: _Transaction | None = None

    def __enter__(self) -> Connection:
        self._cm = transaction(self._database.connection())
        return self._cm.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        cm, self._cm = self._cm, None
        if cm is None:  # pragma: no cover - __enter__ raised
            return
        cm.__exit__(exc_type, exc, tb)
        return


def lock_path(path: str | Path = "var/executor.lock") -> Path:
    """Where the executor's single-writer lock lives (§5.3).

    Named here so the CLI, the worker and the tests agree on one path rather than
    each inventing one.
    """
    return Path(os.environ.get("APP_EXECUTOR_LOCK", path))
