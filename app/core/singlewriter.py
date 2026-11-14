"""The executor's single-writer lock.

FINAL.md §5.3:

> The executor takes a file lock (``var/executor.lock``), so there is a single
> writer for money state.

Nothing took it. ``db.lock_path`` named the path and honoured
``APP_EXECUTOR_LOCK``, and was called from nowhere. The whole design rests on one
writer, so until this exists two ``make worker`` invocations both write money state
- two processes each believing they are the executor.

**Why a lock file rather than SQLite.** SQLite serialises, which prevents corrupt
writes, but it does not tell an operator that a second executor exists. A lock file
is visible, records the pid, and can be removed after a crash. That is the property
that matters here: two executors must fail at startup with a readable message, not
interleave writes and be reconciled afterwards.

**The stale case is the one that matters.** A ``kill -9`` between creating and
removing the lock leaves it behind, and without a reclaim the executor is dead
forever with no in-band way out - the same shape as the kill switch's unclearable
trip (D-B21). Only a lock whose holder is proven gone may be reclaimed. Age is
never proof of death: a healthy executor may hold the lock for days.

**Never signal a pid to test it.** ``os.kill(pid, 0)`` is the idiomatic POSIX
liveness probe, and on Windows CPython implements ``os.kill`` as
``TerminateProcess`` regardless of the signal argument - so it *terminates* the
process if it exists. Measured during this module's own test run: calling it on the
test process's own pid killed the process instantly (D-B27). The POSIX branch keeps
the probe; Windows asks through ``OpenProcess``, which looks without signalling.
"""

from __future__ import annotations

import os
import platform
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from app.core import db

__all__ = [
    "DEFAULT_STALE_AFTER_S",
    "ExecutorLockHeldError",
    "executor_lock",
    "is_held",
    "reclaim_if_stale",
]

#: Legacy timeout argument default; age no longer authorizes reclamation.
DEFAULT_STALE_AFTER_S: float = 3600.0


class ExecutorLockHeldError(RuntimeError):
    """Another executor holds the lock.

    Deliberately a ``RuntimeError`` and not an ``sqlite3.Error``: a caller must not
    be able to swallow this with a broad storage handler and carry on writing money
    state.
    """


def _pid_alive_windows(pid: int) -> bool:
    """Is ``pid`` running, asked through ``OpenProcess``, never signalled.

    ``OpenProcess`` with limited-information access succeeds for a live pid
    regardless of permission to signal it, and fails for a dead one. The handle is
    closed immediately.
    """
    import ctypes
    from ctypes import wintypes

    # Windows process-rights flag. Lower case: it is a local variable, and an
    # ALL_CAPS name made ruff flag it as a module constant.
    process_query_limited = 0x1000

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(process_query_limited, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER proves the PID does not exist. Access denied
        # or any unrecognized failure must preserve the writer's lock.
        return ctypes.get_last_error() != 87
    kernel32.CloseHandle(handle)
    return True


def _pid_alive(pid: int) -> bool:
    """Is ``pid`` running? Never signal it.

    ``os.kill(pid, 0)`` is correct on POSIX and **terminates on Windows**, so this
    branches before calling it. See the module docstring.
    """
    if platform.system() == "Windows":
        return _pid_alive_windows(pid)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False
    return True


def _read_holder(path: Path) -> tuple[int | None, float]:
    """The pid and the time the lock was taken, tolerating a damaged file."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, 0.0

    pid: int | None = None
    taken: float = 0.0
    for line in raw.splitlines():
        if line.startswith("pid="):
            try:
                pid = int(line[4:].strip())
            except ValueError:
                pid = None
        elif line.startswith("at="):
            try:
                taken = float(line[3:].strip())
            except ValueError:
                taken = 0.0
    return pid, taken


def _acquire(path: Path) -> None:
    """Create the lock file, or raise."""
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ExecutorLockHeldError(
            f"{path} is held by another executor. §5.3 requires a single writer "
            "for money state: two executors would each believe they are the "
            "executor, and both would write payee state."
        ) from None

    os.write(fd, f"pid={os.getpid()}\nat={time.time():.0f}\n".encode("ascii"))
    os.close(fd)


def is_held(path: str | Path) -> bool:
    """Does the lock exist right now?"""
    return Path(path).exists()


def reclaim_if_stale(path: str | Path, *, stale_after_s: float = DEFAULT_STALE_AFTER_S) -> bool:
    """Remove the lock only if its holder is proven gone.

    Returns whether it reclaimed. ``False`` means the lock was left alone because
    either there was nothing to reclaim or the holder looked alive.

    ``stale_after_s`` remains for compatibility but never authorizes eviction.
    A truncated file may be an acquisition in progress, so it is preserved.
    """
    path = Path(path)
    if not path.exists():
        return False

    _ = stale_after_s
    pid, _taken = _read_holder(path)
    if pid is None or _pid_alive(pid):
        return False

    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


@contextmanager
def executor_lock(path: str | Path | None = None, *, wait_s: float = 0.0) -> Iterator[Path]:
    """Hold the executor lock for the duration of the block.

    Acquiring a stale lock is the caller's job: call :func:`reclaim_if_stale` first
    if a previous executor may have been killed. Age never proves a holder dead.
    Passing ``stale_after_s`` here would be ambiguous about whose timeout applies,
    so it is not a parameter of this function.
    ``wait_s`` waits for a lock that is genuinely held rather than raising. Zero by
    default, because a second executor starting up should fail loudly and quickly -
    the operator just started something twice. A *demoted* worker that would watch
    without writing may set it, and must then assert it never takes the write path.

    The pid is written to the file so an operator can tell a live executor from a
    stale one, and so :func:`reclaim_if_stale` can check.
    """
    resolved = Path(path if path is not None else db.lock_path())
    resolved.parent.mkdir(parents=True, exist_ok=True)

    deadline = time.monotonic() + wait_s
    while True:
        try:
            _acquire(resolved)
            break
        except ExecutorLockHeldError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.1)

    try:
        yield resolved
    finally:
        with suppress(FileNotFoundError):
            # Reclaimed underneath us while we held it: not our problem.
            resolved.unlink()
