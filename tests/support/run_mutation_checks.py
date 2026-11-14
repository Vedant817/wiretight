"""Explicit local acceptance experiment: mutate one invariant, then restore exact bytes.

This script is never imported by the product. Run only with --run after committing
the intended test changes; it refuses a dirty tree. Outputs stay in ignored local
artifacts. A killed mutant must cause a test-call failure, not a collection/setup
error. No provider credentials or live test nodes are used.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def changed(source: str, before: str, after: str) -> str:
    assert source.count(before) == 1, "Mutation anchor changed; review experiment"
    return source.replace(before, after, 1)


def experiments():
    executor = "app/workers/executor.py"
    adversaries = "tests/unit/test_execution_adversaries.py::"
    return [
        (
            "cooling_deadline",
            "app/core/packets.py",
            lambda s: changed(
                s,
                "if datetime.fromisoformat(effective_cooling) > utcnow():",
                "if False and datetime.fromisoformat(effective_cooling) > utcnow():",
            ),
            [adversaries + "test_tampered_cooling_deadline_cannot_override_signed_callback_window"],
        ),
        (
            "approval_consumption",
            executor,
            lambda s: changed(
                s,
                s[
                    s.index("            if not consumed:") : s.index(
                        "            elif (", s.index("            if not consumed:")
                    )
                ],
                "            if not consumed:\n                pass\n",
            ),
            [
                "tests/unit/test_real_executor.py::test_approved_payment_executes_once_and_uses_real_boundaries"
            ],
        ),
        (
            "idempotency_recovery_key",
            executor,
            lambda s: changed(
                s,
                'intent["request_id"], from_created_at=intent["created_at"]',
                'str(uuid4()), from_created_at=intent["created_at"]',
            ),
            [adversaries + "test_timeout_recovery_and_retry_keep_the_original_idempotency_key"],
        ),
        (
            "webhook_signature",
            "app/api/main.py",
            lambda s: changed(
                s,
                "if not hmac.compare_digest(expected, signature):",
                "if False and not hmac.compare_digest(expected, signature):",
            ),
            [
                adversaries
                + "test_webhook_claims_do_not_override_provider_get_and_forgery_is_refused"
            ],
        ),
        (
            "halt_before_post",
            executor,
            lambda s: changed(s, "        killswitch.load(conn, self.halt_file).guard()\n", ""),
            [adversaries + "test_control_change_after_claim_prevents_the_money_post[halt]"],
        ),
        (
            "approver_role",
            "app/api/operators.py",
            lambda s: remove_queue_role(s),
            [adversaries + "test_ops_cannot_queue_a_fully_approved_packet"],
        ),
        (
            "tie_out_clean",
            "app/core/reconciliation.py",
            lambda s: changed(s, "clean = residual == 0 and not unexplained", "clean = True"),
            [
                "tests/unit/test_reconciliation_runtime.py::"
                "test_actual_cash_mismatch_is_unexplained_even_when_journal_balances"
            ],
        ),
        (
            "unmapped_payout",
            "app/core/reconciliation.py",
            lambda s: changed(
                s,
                'row["source_type"] == "PAYOUT"',
                'False and row["source_type"] == "PAYOUT"',
            ),
            [
                "tests/unit/test_reconciliation_runtime.py::"
                "test_unmapped_provider_payout_is_not_falsely_cleared_by_zero_residual"
            ],
        ),
        (
            "webhook_id_reuse",
            "app/api/main.py",
            lambda s: changed(
                s,
                'if existing["raw_sha256"] != digest:',
                'if False and existing["raw_sha256"] != digest:',
            ),
            ["tests/unit/test_product_webhooks.py::test_bad_signature_and_malformed_input"],
        ),
        (
            "unknown_webhook_event",
            "app/api/main.py",
            lambda s: changed(
                s,
                "event = WebhookEvent.model_validate_json(raw)",
                "event = WebhookEvent(id='x', name='x', data={})",
            ),
            [
                "tests/unit/test_product_webhooks.py::"
                "test_unknown_event_name_is_only_a_poll_hint_and_malformed_events_are_refused"
            ],
        ),
    ]


def remove_queue_role(source: str) -> str:
    start = source.index("    def queue_action(")
    first = source.index('        if session.role != "approver":', start)
    last = source.index("        try:", first)
    return source[:first] + source[last:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / "output/playwright/acceptance-evidence/mutations"
    output.mkdir(parents=True, exist_ok=True)
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=root), (
        "Commit intended changes first"
    )
    results = []
    for name, relative, mutate, nodes in experiments():
        path = root / relative
        original = path.read_bytes()
        source = original.decode("utf-8").replace("\r\n", "\n")
        mutant = mutate(source)
        ast.parse(mutant)  # A syntax error is not evidence that an invariant test bites.
        xml = output / (name + ".xml")
        before = hashlib.sha256(original).hexdigest()
        try:
            path.write_bytes(mutant.encode("utf-8"))
            command = [
                "uv",
                "run",
                "pytest",
                *nodes,
                "-q",
                "--timeout=180",
                "--tb=short",
                "--junitxml",
                str(xml),
            ]
            run = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=240)
            log = run.stdout + run.stderr
            (output / (name + ".txt")).write_text(log, encoding="utf-8")
            failures = []
            errors = []
            if xml.exists():
                for case in ET.parse(xml).getroot().iter("testcase"):
                    if case.find("failure") is not None:
                        failures.append(case.attrib["name"])
                    if case.find("error") is not None:
                        errors.append(case.attrib["name"])
            killed = run.returncode == 1 and bool(failures) and not errors
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
            clean = not subprocess.check_output(["git", "status", "--porcelain"], cwd=root)
            assert clean, "Restoration left a dirty tree"
        result = {
            "mutation": name,
            "file": relative,
            "nodes": nodes,
            "exit": run.returncode,
            "killed": killed,
            "failed_tests": failures,
            "setup_errors": errors,
            "original_sha256": before,
            "restored_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "git_clean": clean,
        }
        results.append(result)
        (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(
            name + " -> " + (", ".join(failures) if killed else "SURVIVED/INVALID; review log"),
            flush=True,
        )
        print("restored bytes; git status --porcelain empty", flush=True)
        if not killed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
