"""Crash/restart the actual money worker process; provider transport is test-only."""

# ruff: noqa: F811
import json
import subprocess
import sys
from pathlib import Path

from app.core import operators
from tests.unit.test_operators_signing import domain  # noqa: F401
from tests.unit.test_real_executor import execution  # noqa: F401


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
