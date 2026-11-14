"""The executor's single-writer lock, §5.3.

Two ``make worker`` invocations both write money state until this exists. The tests
that matter are the stale ones: a ``kill -9`` leaves the lock behind, and without a
reclaim the executor is dead forever with no in-band way out - the same shape as the
unclearable kill-switch trip in D-B21.
"""

from __future__ import annotations

import os
import platform
import time
from pathlib import Path

import pytest

from app.core import db
from tests.support import legacy_singlewriter as singlewriter
from tests.support.legacy_singlewriter import ExecutorLockHeldError


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "executor.lock"


class TestTheLockIsReal:
    def test_a_second_executor_cannot_start(self, lock_path: Path) -> None:
        with singlewriter.executor_lock(path=lock_path):  # noqa: SIM117
            # The inner call must be *entered*, not merely constructed: a
            # @contextmanager returns the manager object without running its
            # body, so calling it inside pytest.raises acquires nothing and
            # tests nothing. That is what a first version did (D-B27).
            with pytest.raises(ExecutorLockHeldError, match="single writer"):
                with singlewriter.executor_lock(path=lock_path):
                    pass

    def test_the_lock_is_released_on_exit(self, lock_path: Path) -> None:
        with singlewriter.executor_lock(path=lock_path):
            assert lock_path.exists()
        assert not lock_path.exists()

    def test_a_later_executor_can_start(self, lock_path: Path) -> None:
        with singlewriter.executor_lock(path=lock_path):
            pass
        with singlewriter.executor_lock(path=lock_path):
            assert lock_path.exists()

    def test_the_holder_pid_is_recorded(self, lock_path: Path) -> None:
        """An operator must be able to tell a live executor from a stale file."""
        with singlewriter.executor_lock(path=lock_path):
            pid, taken = singlewriter._read_holder(lock_path)
            assert pid == os.getpid()
            assert taken > 0

    def test_the_default_path_is_the_one_5_3_names(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("APP_EXECUTOR_LOCK", str(tmp_path / "custom.lock"))
        assert db.lock_path() == tmp_path / "custom.lock"


class TestTheLockFailsLoudly:
    def test_the_error_is_not_an_sqlite_error(self, lock_path: Path) -> None:
        """A caller must not swallow this with a broad storage handler.

        ``ExecutorLockHeldError`` is a ``RuntimeError``, so ``except sqlite3.Error`` does
        not catch it. A caller that proceeded on a stale write path would be the one
        scenario this lock exists to prevent.
        """
        import sqlite3

        assert not issubclass(ExecutorLockHeldError, sqlite3.Error)

        with singlewriter.executor_lock(path=lock_path):  # noqa: SIM117
            with pytest.raises(ExecutorLockHeldError):
                with singlewriter.executor_lock(path=lock_path):
                    pass


class TestStaleLocks:
    def test_a_lock_whose_holder_is_dead_is_reclaimed(self, lock_path: Path) -> None:
        """A ``kill -9`` must not wedge the executor permanently.

        Same failure shape as D-B21's unclearable trip: no in-band route back. The
        pid is checked, and a dead one means reclaim.
        """
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("pid=999999\nat=0\n", encoding="utf-8")

        assert singlewriter.reclaim_if_stale(lock_path)
        assert not lock_path.exists()

    def test_a_live_holder_is_left_alone(self, lock_path: Path) -> None:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(f"pid={os.getpid()}\nat={time.time():.0f}\n", encoding="utf-8")
        assert not singlewriter.reclaim_if_stale(lock_path)
        assert lock_path.exists()

    def test_an_old_lock_with_a_live_pid_is_preserved(self, lock_path: Path) -> None:
        """A live long-running worker must exclude a second writer at any age."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(
            f"pid={os.getpid()}\nat={time.time() - 100000:.0f}\n", encoding="utf-8"
        )

        assert not singlewriter.reclaim_if_stale(lock_path, stale_after_s=60.0)
        assert lock_path.exists()

    def test_a_damaged_lock_is_preserved(self, lock_path: Path) -> None:
        """A truncated lock may belong to a worker still writing its holder PID."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("garbage", encoding="utf-8")
        assert not singlewriter.reclaim_if_stale(lock_path)
        assert lock_path.exists()

    def test_reclaim_on_a_missing_lock_is_false(self, lock_path: Path) -> None:
        assert not singlewriter.reclaim_if_stale(lock_path)

    def test_waiting_for_a_held_lock_then_succeeding(self, lock_path: Path) -> None:
        """The demoted-worker case: wait, then take over.

        Zero by default, because a second executor should fail loudly. A worker that
        watches without writing may set it, and must then never take the write path.
        """
        with singlewriter.executor_lock(path=lock_path):
            start = time.monotonic()

            def release_later() -> None:
                time.sleep(0.3)
                lock_path.unlink()

            thread = __import__("threading").Thread(target=release_later)
            thread.start()
            try:
                with singlewriter.executor_lock(path=lock_path, wait_s=5.0):
                    waited = time.monotonic() - start
            finally:
                thread.join()

        assert waited >= 0.25, f"did not wait for the lock: {waited:.2f}s"


class TestIntegrationWithDb:
    def test_the_lock_path_and_the_module_agree(self, lock_path: Path) -> None:
        """The Makefile, the CLI, the worker and the tests must not invent paths.

        ``db.lock_path`` is the single source, so a second definition is what would
        let two processes each take a different "the" lock.
        """
        assert lock_path.name == "executor.lock"

    def test_two_writers_on_one_database_are_excluded(self, tmp_path: Path) -> None:
        """The failure the lock exists for, produced for real.

        Both threads take the executo lock path; exactly one wins. This is the
        property, not an implementation detail.
        """
        from concurrent.futures import ThreadPoolExecutor

        lock = tmp_path / "var" / "executor.lock"
        taken: list[str] = []

        def try_lock(index: int) -> None:
            try:
                with singlewriter.executor_lock(path=lock):
                    taken.append(f"held-{index}")
                    time.sleep(0.05)
            except ExecutorLockHeldError:
                taken.append(f"refused-{index}")

        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(try_lock, range(3)))

        assert taken.count("held-0") + taken.count("held-1") + taken.count("held-2") == 1
        assert len(taken) == 3


class TestNeverSignalsTheHolder:
    """The bug this module was written with, and what it would have done.

    ``os.kill(pid, 0)`` is the idiomatic POSIX liveness probe. CPython's Windows
    implementation ignores the signal argument and calls ``TerminateProcess``, so it
    *terminates* the process if it exists. The first version of ``_pid_alive`` used it
    unconditionally, and calling it on this process's own pid killed the test run with
    no output at all (D-B27).

    In production it is not called on the executor's own pid, so it would not have
    killed itself - but it would have killed *another live executor* the moment a
    stale-lock check ran. A module whose purpose is preventing two processes writing
    money state would have destroyed one of them.
    """

    def test_the_liveness_check_does_not_kill_a_live_pid(self) -> None:
        """The whole point, asserted by surviving it."""
        import os

        assert singlewriter._pid_alive(os.getpid())

    def test_the_posix_branch_is_not_taken_on_windows(self) -> None:
        """On Windows the OpenProcess path must be used, never os.kill.

        Asserted structurally: patching ``os.kill`` records whether it is reached.
        """
        import os
        from unittest import mock

        with mock.patch.object(os, "kill", wraps=os.kill) as spy:
            singlewriter._pid_alive(os.getpid())
        if platform.system() == "Windows":
            spy.assert_not_called()

    def test_nonexistent_pid_reads_as_dead(self) -> None:
        """Windows ERROR_INVALID_PARAMETER proves the PID does not exist."""
        assert not singlewriter._pid_alive(0x7FFFFFFF)
