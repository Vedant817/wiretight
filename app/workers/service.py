"""Sandbox worker for refresh, polling and explicitly approved execution jobs.

REFRESH jobs are read-only and safe to replay after a crash. EXECUTE jobs recheck
human approval and all money guards. Planning and reconciliation use durable, authenticated jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
from pathlib import Path

from pydantic import ValidationError

from app.config import SandboxGuardError, WorkerSettings, validate_product
from app.core import audit, db
from app.core.operators import utcnow
from app.core.process_lock import ProcessLockHeldError, exclusive_process
from app.integrations.airwallex import AirwallexClient, ProviderError
from app.logging_config import configure_logging


def heartbeat(database: db.Database, detail: str, *, ready: bool = False) -> None:
    with database.transaction() as conn:
        conn.execute(
            "INSERT INTO worker_health(id,ready,detail,checked_at) VALUES(1,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET ready=excluded.ready,detail=excluded.detail,"
            "checked_at=excluded.checked_at",
            (int(ready), detail, utcnow().isoformat()),
        )


def refresh(database: db.Database, client: AirwallexClient) -> bool:
    """Persist a genuine observation and finish pending refresh jobs atomically."""
    conn = database.connection()
    jobs = conn.execute(
        "SELECT j.id,a.enabled FROM provider_job j "
        "JOIN operator_auth a ON a.user_id=j.requested_by "
        "WHERE j.kind='REFRESH' AND j.state='PENDING' ORDER BY j.created_at"
    ).fetchall()
    with database.transaction() as tx:
        for job in jobs:
            if not job["enabled"]:
                tx.execute(
                    "UPDATE provider_job SET state='FAILED',error='requester_revoked',"
                    "updated_at=? WHERE id=?",
                    (utcnow().isoformat(), job["id"]),
                )
    try:
        db.assert_no_write_lock(conn, doing="refresh Airwallex balances")
        balances = client.get_balances()
        if client.clock_skew_s is None or abs(client.clock_skew_s) > 120:
            raise ProviderError("clock_unverified")
        currencies = [item.currency for item in balances]
        if len(currencies) != len(set(currencies)) or any(
            not item.available_amount.is_finite() for item in balances
        ):
            raise ProviderError("invalid_balances")
        canonical = audit.canonical_json({"balances": [item.model_dump() for item in balances]})
        observed_at = utcnow().isoformat()
        with database.transaction() as tx:
            tx.execute(
                "INSERT INTO provider_snapshot(kind,subject,canonical_json,observed_at) "
                "VALUES('BALANCES','wallet',?,?) ON CONFLICT(kind,subject) DO UPDATE SET "
                "canonical_json=excluded.canonical_json,observed_at=excluded.observed_at",
                (canonical, observed_at),
            )
            for job in jobs:
                # Revocation during the HTTP request also cancels the job.
                active = tx.execute(
                    "SELECT a.enabled,j.state FROM provider_job j JOIN operator_auth a "
                    "ON a.user_id=j.requested_by WHERE j.id=?",
                    (job["id"],),
                ).fetchone()
                if active and active["state"] == "PENDING":
                    tx.execute(
                        "UPDATE provider_job SET state=?,result_json=?,error=?,updated_at=? "
                        "WHERE id=?",
                        (
                            "DONE" if active["enabled"] else "FAILED",
                            audit.canonical_json(
                                {"snapshot": "BALANCES", "observed_at": observed_at}
                            )
                            if active["enabled"]
                            else None,
                            None if active["enabled"] else "requester_revoked",
                            observed_at,
                            job["id"],
                        ),
                    )
            audit.append(
                tx,
                "provider.balances_observed",
                {
                    "observed_at": observed_at,
                    "currencies": sorted(currencies),
                    "refresh_jobs": [job["id"] for job in jobs if job["enabled"]],
                },
            )
        heartbeat(database, "provider_connected; installation_checks_pending")
        return True
    except (ProviderError, ValidationError) as exc:
        category = exc.category if isinstance(exc, ProviderError) else "invalid_response"
        with database.transaction() as tx:
            for job in jobs:
                tx.execute(
                    "UPDATE provider_job SET state='FAILED',error=?,updated_at=? "
                    "WHERE id=? AND state='PENDING'",
                    (category, utcnow().isoformat(), job["id"]),
                )
        heartbeat(database, "provider_" + category)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="perform one real read, then exit")
    args = parser.parse_args()
    database: db.Database | None = None
    client: AirwallexClient | None = None
    stop = threading.Event()
    try:
        settings = WorkerSettings()
        validate_product(settings)
        configure_logging(
            {
                **os.environ,
                "AWX_API_KEY": settings.awx_api_key,
                "AWX_CLIENT_ID": settings.awx_client_id,
            },
            level=settings.log_level,
        )
        database = db.Database(settings.app_db_path)
        environment = {
            **os.environ,
            "AWX_ENV": settings.awx_env,
            "AWX_BASE_URL": settings.awx_base_url,
        }
        settings.check_startup(environment)
        if (
            settings.awx_mode != "live"
            or os.environ.get("DEMO_MODE")
            or os.environ.get("APP_DEMO_TIMING")
        ):
            raise SandboxGuardError("Product refresh worker requires live sandbox mode")
        if not 1 <= settings.poll_interval_s <= 60:
            raise SandboxGuardError("Poll interval must be between 1 and 60 seconds")
        client = AirwallexClient(
            settings.awx_client_id,
            settings.awx_api_key,
            timeout=settings.awx_http_timeout_s,
            api_version=settings.awx_api_version,
            login_as=settings.awx_login_as,
        )
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        with exclusive_process(Path(settings.app_db_path).with_suffix(".refresh.lock")):
            while not stop.is_set():
                okay = refresh(database, client)
                if okay:
                    from app.core import killswitch, runtime_policy
                    from app.workers.executor import Executor
                    from app.workers.jobs import process_actions
                    from app.workers.operations import reconcile_open_runs

                    try:
                        executor = Executor(
                            database,
                            client,
                            policy_path=Path(settings.app_policy_path),
                            key_dir=Path(settings.app_key_dir),
                            seal_dir=Path(settings.app_audit_checkpoint_dir),
                            halt_file=Path(settings.app_halt_file),
                            lock_file=Path(settings.app_db_path).with_suffix(".execution.lock"),
                            rp_id=settings.webauthn_rp_id,
                            origin=settings.webauthn_origin,
                        )
                        # Provider observations continue even while the money controls are halted.
                        executor.poll()
                        process_actions(executor)
                        matched = reconcile_open_runs(executor)
                        conn = database.connection()
                        executor._trust(conn)
                        runtime_policy.load_runtime_policy(
                            conn, executor.policy_path, executor.passkeys
                        )
                        killswitch.load(conn, executor.halt_file).guard()
                        heartbeat(
                            database,
                            "provider_connected; ready" if matched else "reconciliation_mismatch",
                            ready=matched,
                        )
                    except Exception as exc:
                        # No secret-bearing exception text crosses the logging boundary.
                        import logging

                        logging.getLogger("wiretight").warning(
                            {
                                "event": "worker.controls_unavailable",
                                "error_type": type(exc).__name__,
                            }
                        )
                        heartbeat(
                            database, "installation_trust_policy_or_reconciliation_unavailable"
                        )
                        okay = False
                if args.once:
                    return 0 if okay else 1
                stop.wait(settings.poll_interval_s)
            heartbeat(database, "worker_stopped")
        return 0
    except (SandboxGuardError, ValidationError):
        if database:
            heartbeat(database, "setup_invalid_or_missing_credentials")
        print(
            json.dumps(
                {"event": "worker.refused", "reason": "check_sandbox_credentials_and_config"}
            )
        )
        return 2
    except ProcessLockHeldError:
        print(json.dumps({"event": "worker.refused", "reason": "worker_lock_held"}))
        return 2
    except Exception as exc:
        if database:
            heartbeat(database, "worker_unavailable")
        print(json.dumps({"event": "worker.failed", "error_type": type(exc).__name__}))
        return 1
    finally:
        if client:
            client.close()
        if database:
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
