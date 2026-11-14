"""Kernel-held process exclusion, automatically released on crash.

The lock inode persists. Never unlink or reclaim it by age or PID; doing so
would let different processes hold locks on different files at the same path.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class ProcessLockHeldError(RuntimeError):
    pass


@contextmanager
def exclusive_process(path: str | Path) -> Iterator[None]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_CREAT | os.O_RDWR, 0o600)
    held = False
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\x00")
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = True
        except OSError:
            raise ProcessLockHeldError("Another worker holds the executor process lock") from None
        yield
    finally:
        if held:
            if sys.platform == "win32":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
