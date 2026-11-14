"""Test-only process crash with durable provider state behind the HTTP client."""

import argparse
import json
import os
from pathlib import Path

import httpx
import time_machine

from app.core import db
from app.integrations.airwallex import AirwallexClient
from app.workers.executor import Executor
from tests.unit.test_real_executor import ProviderBoundary


def main():
    parser = argparse.ArgumentParser()
    for flag in ("db", "keys", "seals", "policy", "lock", "halt", "state", "at", "packet"):
        parser.add_argument("--" + flag, required=True)
    parser.add_argument("--crash", action="store_true")
    parser.add_argument("--job-id")
    args = parser.parse_args()
    state_path = Path(args.state)

    class DurableBoundary(ProviderBoundary):
        def __init__(self):
            super().__init__()
            value = json.loads(state_path.read_text(encoding="utf-8"))
            for key in ("balance", "beneficiaries", "transfers", "posts"):
                setattr(self, key, value[key])

        def handle(self, request):
            response = super().handle(request)
            value = {
                key: getattr(self, key)
                for key in ("balance", "beneficiaries", "transfers", "posts")
            }
            staged = state_path.with_suffix(".pending")
            with staged.open("w", encoding="utf-8") as stream:
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
            staged.replace(state_path)
            if args.crash and request.url.path.endswith("/transfers/create"):
                os._exit(91)
            return response

    with time_machine.travel(args.at, tick=False), db.Database(args.db) as database:
        provider = DurableBoundary()
        client = AirwallexClient(
            "fixture-id", "fixture-key", transport=httpx.MockTransport(provider.handle)
        )
        try:
            executor = Executor(
                database,
                client,
                policy_path=Path(args.policy),
                key_dir=Path(args.keys),
                seal_dir=Path(args.seals),
                halt_file=Path(args.halt),
                lock_file=Path(args.lock),
            )
            if args.job_id:
                from app.workers.jobs import process_actions

                process_actions(executor)
                print(
                    database.connection()
                    .execute("SELECT state FROM provider_job WHERE id=?", (args.job_id,))
                    .fetchone()[0]
                )
            else:
                print(executor.execute(args.packet))
        finally:
            client.close()


if __name__ == "__main__":
    main()
