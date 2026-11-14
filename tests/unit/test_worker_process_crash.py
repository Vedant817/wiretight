"""Crash/restart the actual money worker process; provider transport is test-only."""

# ruff: noqa: F811
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.core import operators
from app.local import stop_child
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401


@pytest.mark.compliance("T-15")
def test_real_worker_process_death_then_restart_never_reposts(execution, tmp_path):
    executor, provider, packet_id, _ = execution
    conn = executor.database.connection()
    actor = conn.execute("SELECT id FROM user ORDER BY created_at,id LIMIT 1").fetchone()[0]
    now = operators.utcnow().isoformat()
    conn.execute(
        "INSERT INTO provider_job(id,kind,requested_by,request_json,state,created_at,updated_at) "
        "VALUES('crash-job','EXECUTE',?,?,'PENDING',?,?)",
        (actor, json.dumps({"packet_id": packet_id}), now, now),
    )
    state = tmp_path / "provider-state.json"
    state.write_text(
        json.dumps(
            {
                key: getattr(provider, key)
                for key in ("balance", "beneficiaries", "transfers", "posts")
            }
        ),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-m",
        "tests.support.money_crash_worker",
        "--db",
        str(executor.database.path),
        "--keys",
        str(executor.key_dir),
        "--seals",
        str(executor.seal_dir),
        "--policy",
        str(executor.policy_path),
        "--lock",
        str(executor.lock_file),
        "--halt",
        str(executor.halt_file),
        "--state",
        str(state),
        "--at",
        operators.utcnow().isoformat(),
        "--packet",
        packet_id,
        "--job-id",
        "crash-job",
    ]
    crashed = subprocess.run(
        [*command, "--crash"],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert crashed.returncode == 91, crashed.stderr
    conn = executor.database.connection()
    assert (
        conn.execute("SELECT state FROM execution_intent WHERE kind='TRANSFER'").fetchone()[0]
        == "PREPARED"
    )
    assert (
        conn.execute("SELECT state FROM provider_job WHERE id='crash-job'").fetchone()[0]
        == "PENDING"
    )
    resumed = subprocess.run(
        command, cwd=Path(__file__).parents[2], capture_output=True, text=True, timeout=45
    )
    assert resumed.returncode == 0, resumed.stderr
    assert resumed.stdout.strip() == "DONE"
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert len(persisted["transfers"]) == 1
    assert len([row for row in persisted["posts"] if row[0] == "/transfers/create"]) == 1
    assert conn.execute("SELECT COUNT(*) FROM approval_consumption").fetchone()[0] == 1


def test_two_actual_worker_processes_cannot_double_execute(execution, tmp_path):
    executor, provider, packet_id, _ = execution
    state = tmp_path / "concurrent-provider.json"
    state.write_text(
        json.dumps(
            {
                key: getattr(provider, key)
                for key in ("balance", "beneficiaries", "transfers", "posts")
            }
        ),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-m",
        "tests.support.money_crash_worker",
        "--db",
        str(executor.database.path),
        "--keys",
        str(executor.key_dir),
        "--seals",
        str(executor.seal_dir),
        "--policy",
        str(executor.policy_path),
        "--lock",
        str(executor.lock_file),
        "--halt",
        str(executor.halt_file),
        "--state",
        str(state),
        "--at",
        operators.utcnow().isoformat(),
        "--packet",
        packet_id,
    ]
    children = [
        subprocess.Popen(
            command,
            cwd=Path(__file__).parents[2],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for _ in range(2)
    ]
    results = [(child.communicate(timeout=45), child.returncode) for child in children]
    assert any(code == 0 for _, code in results)
    for (_, error), code in results:
        assert code == 0 or "ProcessLockHeldError" in error, error
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert len(persisted["transfers"]) == 1
    assert len([row for row in persisted["posts"] if row[0] == "/transfers/create"]) == 1
    assert (
        executor.database.connection()
        .execute("SELECT COUNT(*) FROM approval_consumption")
        .fetchone()[0]
        == 1
    )


@pytest.mark.compliance("T-15")
def test_kill_after_durable_claim_before_money_post_recovers_lookup_only(execution, tmp_path):
    executor, provider, packet_id, _ = execution
    state = tmp_path / "before-call-state.json"
    state.write_text(
        json.dumps(
            {k: getattr(provider, k) for k in ("balance", "beneficiaries", "transfers", "posts")}
        ),
        encoding="utf-8",
    )
    command = [sys.executable, "-m", "tests.support.money_crash_worker"]
    values = {
        "db": executor.database.path,
        "keys": executor.key_dir,
        "seals": executor.seal_dir,
        "policy": executor.policy_path,
        "lock": executor.lock_file,
        "halt": executor.halt_file,
        "state": state,
        "at": operators.utcnow().isoformat(),
        "packet": packet_id,
    }
    for flag, value in values.items():
        command.extend(["--" + flag, str(value)])
    with (tmp_path / "before-call.log").open("wb") as log:
        worker = subprocess.Popen(
            [*command, "--pause-before-call"],
            stdout=log,
            stderr=log,
            cwd=Path(__file__).parents[2],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        try:
            deadline = time.monotonic() + 30
            while not state.with_suffix(".claimed").exists() and time.monotonic() < deadline:
                assert worker.poll() is None, "Worker exited before claim barrier"
                time.sleep(0.05)
            assert state.with_suffix(".claimed").exists(), "Durable claim not reached"
            conn = executor.database.connection()
            assert conn.execute("SELECT COUNT(*) FROM approval_consumption").fetchone()[0] == 1
            assert json.loads(state.read_text(encoding="utf-8"))["transfers"] == {}
        finally:
            stop_child(worker)
    recovered = subprocess.run(
        command, capture_output=True, text=True, timeout=45, cwd=Path(__file__).parents[2]
    )
    assert recovered.returncode == 0, recovered.stderr
    assert recovered.stdout.strip() == "AMBIGUOUS"
    durable = json.loads(state.read_text(encoding="utf-8"))
    assert durable["transfers"] == {}
    assert not any(path == "/transfers/create" for path, _ in durable["posts"])
    assert conn.execute("SELECT COUNT(*) FROM approval_consumption").fetchone()[0] == 1
