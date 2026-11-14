"""Fenced provider observations and exact, deduplicated financial ledger postings.

Cash total is reconciled separately from available balance: reservations are not
cash withdrawals. A missing total or incomplete history never becomes a zero.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.core import audit, db, ledger
from app.core.operators import utcnow
from app.integrations.airwallex import AirwallexClient
from app.money import parse_money, to_money_string


class ReconciliationError(RuntimeError):
    pass


def _cash(client: AirwallexClient) -> dict[str, Decimal]:
    result = {}
    for balance in client.get_balances():
        data = balance.model_dump()
        if data.get("account_type") != "cash" or "total_amount" not in data:
            raise ReconciliationError("Actual cash total balances are required for reconciliation")
        amount = parse_money(str(data["total_amount"]))
        for component in ("pending_amount", "reserved_amount", "prepayment_amount"):
            if component not in data or parse_money(str(data[component])) != 0:
                raise ReconciliationError("Cash has pending/reserved amounts; defer reconciliation")
        if not amount.is_finite() or balance.currency in result:
            raise ReconciliationError("Invalid or duplicate cash total")
        result[balance.currency] = amount
    return result


def snapshot(client: AirwallexClient) -> tuple[dict[str, Decimal], dict[str, dict[str, Any]]]:
    before = _cash(client)
    # Full history is necessary: a transaction created before the run may settle
    # during it. A recent-created-at window would silently miss that movement.
    rows = client.financial_transactions(
        start="1970-01-01T00:00:00+00:00", end=utcnow().isoformat()
    )
    settled: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("status") not in {"PENDING", "SETTLED", "CANCELLED"}:
            raise ReconciliationError("Unknown financial transaction status")
        if row["status"] != "SETTLED":
            continue
        for key in ("id", "currency", "net", "source_id", "source_type", "transaction_type"):
            if row.get(key) is None:
                raise ReconciliationError("Financial transaction fields are missing")
        net = parse_money(str(row["net"]))
        if not net.is_finite():
            raise ReconciliationError("Financial amount is not finite")
        to_money_string(net, row["currency"])
        if row["id"] in settled and audit.canonical_json(
            settled[row["id"]]
        ) != audit.canonical_json(row):
            raise ReconciliationError("Conflicting financial transaction IDs")
        settled[row["id"]] = row
    if _cash(client) != before:
        raise ReconciliationError("Cash balances changed during observation; retry without posting")
    return before, settled


def open_run(
    conn: db.Connection, client: AirwallexClient, *, operation_id: str | None = None
) -> str:
    # Durable job identity survives a crash after baseline commit but before acknowledgement.
    if operation_id and conn.execute("SELECT 1 FROM run WHERE id=?", (operation_id,)).fetchone():
        if not conn.execute(
            "SELECT 1 FROM audit_log WHERE kind='run.opened' "
            "AND json_extract(payload_json,'$.run_id')=?",
            (operation_id,),
        ).fetchone():
            raise ReconciliationError("Run baseline has no audit evidence")
        return operation_id
    db.assert_no_write_lock(conn, doing="capture opening cash and financial history")
    balances, rows = snapshot(client)
    identifier = operation_id or str(uuid4())
    now = utcnow().isoformat()
    with db.transaction(conn):
        if conn.execute("SELECT 1 FROM run WHERE state='OPEN'").fetchone():
            raise ReconciliationError("Close the existing run before opening another")
        conn.execute(
            "INSERT INTO run(id,started_at,opening_balances,state) VALUES(?,?,?,'OPEN')",
            (identifier, now, audit.canonical_json(balances)),
        )
        conn.execute(
            "INSERT INTO run_baseline(run_id,settled_ids,observed_at) VALUES(?,?,?)",
            (identifier, audit.canonical_json(sorted(rows)), now),
        )
        audit.append(
            conn,
            "run.opened",
            {
                "run_id": identifier,
                "opening_balances": balances,
                "settled_ids": sorted(rows),
                "observed_at": now,
            },
        )
    return identifier


def reconcile(conn: db.Connection, client: AirwallexClient, run_id: str) -> bool:
    db.assert_no_write_lock(conn, doing="reconcile actual provider financial transactions")
    balances, rows = snapshot(client)
    with db.transaction(conn):
        run = conn.execute("SELECT * FROM run WHERE id=?", (run_id,)).fetchone()
        baseline = conn.execute("SELECT * FROM run_baseline WHERE run_id=?", (run_id,)).fetchone()
        if not run or not baseline:
            raise ReconciliationError("Run lacks an actual provider opening observation")
        anchor = conn.execute(
            "SELECT payload_json FROM audit_log WHERE kind='run.opened' "
            "AND json_extract(payload_json,'$.run_id')=? ORDER BY seq LIMIT 1",
            (run_id,),
        ).fetchone()
        if not anchor:
            raise ReconciliationError("Opening observation lacks audit evidence")
        bound = json.loads(anchor[0])
        if (
            bound["opening_balances"] != json.loads(run["opening_balances"])
            or bound["settled_ids"] != json.loads(baseline["settled_ids"])
            or bound["observed_at"] != baseline["observed_at"]
        ):
            raise ReconciliationError("Opening observation differs from audited terms")
        opening = {
            key: Decimal(value) for key, value in json.loads(run["opening_balances"]).items()
        }
        initial = set(json.loads(baseline["settled_ids"]))
        if not initial.issubset(rows):
            raise ReconciliationError("Previously observed financial history is missing")
        delta = {key: Decimal(0) for key in opening}
        unexplained: list[str] = []
        now = utcnow().isoformat()
        for identifier, row in rows.items():
            if identifier in initial:
                continue
            net = Decimal(str(row["net"]))
            currency = row["currency"]
            delta[currency] = delta.get(currency, Decimal(0)) + net
            canonical = audit.canonical_json(row)
            digest = hashlib.sha256(canonical.encode()).hexdigest()
            posted = conn.execute(
                "SELECT * FROM financial_posting WHERE financial_id=?", (identifier,)
            ).fetchone()
            if posted:
                if posted["sha256"] != digest or posted["run_id"] != run_id:
                    raise ReconciliationError(
                        "Posted financial transaction changed or belongs to another run"
                    )
                legs = conn.execute(
                    "SELECT account,currency,debit,credit FROM journal_line "
                    "WHERE run_id=? AND source_id=?",
                    (run_id, identifier),
                ).fetchall()
                magnitude = to_money_string(abs(net), currency)
                expected = (
                    sorted(
                        [
                            (
                                "Wallet:" + currency,
                                currency,
                                magnitude if net > 0 else None,
                                magnitude if net < 0 else None,
                            ),
                            (
                                "Provider:" + row["source_type"],
                                currency,
                                magnitude if net < 0 else None,
                                magnitude if net > 0 else None,
                            ),
                        ]
                    )
                    if net
                    else []
                )
                if sorted(tuple(leg) for leg in legs) != expected:
                    raise ReconciliationError(
                        "Posted financial journal legs are missing or changed"
                    )
            else:
                magnitude = to_money_string(abs(net), currency)
                if net:
                    ledger.post(
                        conn,
                        run_id,
                        [
                            ledger.Leg(
                                "Wallet:" + currency,
                                currency,
                                debit=magnitude if net > 0 else None,
                                credit=magnitude if net < 0 else None,
                                source_id=identifier,
                            ),
                            ledger.Leg(
                                "Provider:" + row["source_type"],
                                currency,
                                debit=magnitude if net < 0 else None,
                                credit=magnitude if net > 0 else None,
                                source_id=identifier,
                            ),
                        ],
                    )
                conn.execute(
                    "INSERT INTO financial_posting VALUES(?,?,?,?,?)",
                    (identifier, run_id, canonical, digest, now),
                )
                audit.append(
                    conn,
                    "financial.posted",
                    {
                        "financial_id": identifier,
                        "run_id": run_id,
                        "sha256": digest,
                        "net": net,
                        "currency": currency,
                    },
                )
            if (
                row["source_type"] == "PAYOUT"
                and not conn.execute(
                    "SELECT 1 FROM transfer_attempt WHERE transfer_id=?", (row["source_id"],)
                ).fetchone()
            ):
                unexplained.append(identifier)
        okay = not unexplained and set(balances) == set(opening)
        for currency in set(opening) & set(balances):
            computed = opening[currency] + delta[currency]
            residual = balances[currency] - computed
            clean = residual == 0 and not unexplained
            okay = okay and clean
            tie_out_id = str(uuid4())
            conn.execute(
                "INSERT INTO tie_out(id,run_id,currency,b_open,b_close_computed,b_actual,residual,"
                "state,explanation,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    tie_out_id,
                    run_id,
                    currency,
                    str(opening[currency]),
                    str(computed),
                    str(balances[currency]),
                    str(residual),
                    "RESIDUAL_0.00" if clean else "RESIDUAL_UNEXPLAINED",
                    audit.canonical_json({"unmapped_payouts": unexplained}),
                    now,
                ),
            )
            if not clean:
                conn.execute(
                    "INSERT INTO recon_exception(id,tie_out_id,kind,source_id,reason,created_at) "
                    "VALUES(?,?,'AMOUNT_MISMATCH',NULL,?,?)",
                    (
                        str(uuid4()),
                        tie_out_id,
                        audit.canonical_json(
                            {"residual": str(residual), "unmapped_payouts": unexplained}
                        ),
                        now,
                    ),
                )
        ledger.assert_ledger_balances(conn)
        audit.append(
            conn, "run.reconciled", {"run_id": run_id, "matched": okay, "observed_at": now}
        )
        return okay
