import subprocess
import sys

import pytest

from app.core.process_lock import ProcessLockHeldError, exclusive_process


def test_process_lock_excludes_another_process_and_survives_crash(tmp_path):
    path = tmp_path / "executor.oslock"
    code = """
import os, sys
from app.core.process_lock import exclusive_process, ProcessLockHeldError
try:
    with exclusive_process(sys.argv[1]):
        os._exit(23)
except ProcessLockHeldError:
    sys.exit(2)
"""
    with exclusive_process(path):
        result = subprocess.run([sys.executable, "-c", code, str(path)], timeout=10, check=False)
        assert result.returncode == 2
        with pytest.raises(ProcessLockHeldError), exclusive_process(path):
            pytest.fail("second local holder acquired lock")
    result = subprocess.run([sys.executable, "-c", code, str(path)], timeout=10, check=False)
    assert result.returncode == 23
    with exclusive_process(path):
        assert path.exists()


def test_exception_releases_kernel_lock(tmp_path):
    path = tmp_path / "executor.oslock"
    with pytest.raises(ValueError), exclusive_process(path):
        raise ValueError("application failed")
    with exclusive_process(path):
        assert path.exists()
