"""Double-entry ledger, one balanced set of legs per posting.

FINAL.md §14 (b). Every posting must sum to zero **per currency**: a USD leg
does not balance a EUR leg, and a journal that mixed them would let a currency's
residual hide inside another's.

The property the tests care about is that an unbalanced or single-sided post is
*refused*, not silently corrected. A ledger that fixes up its own mistakes
cannot be used to prove anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core import db
from app.money import parse_money, to_money_string


class UnbalancedError(ValueError):
    """A posting's debits and credits do not sum to zero in every currency."""


@dataclass(frozen=True)
class Leg:
    """One side of one journal entry.

    Exactly one of ``debit`` / ``credit`` must be set. Amounts are decimal
    strings, never floats (§7.3).
    """

    account: str
    currency: str
    debit: str | None = None
    credit: str | None = None
    source_id: str | None = None
    memo: str | None = None

    def __post_init__(self) -> None:
        if self.debit is not None and self.credit is not None:
            raise ValueError(f"leg for {self.account} is both debit and credit")
        if self.debit is None and self.credit is None:
            raise ValueError(f"leg for {self.account} is neither debit nor credit")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _totals(legs: Sequence[Leg]) -> dict[str, Decimal]:
    """Debit-minus-credit per currency."""
    totals: dict[str, Decimal] = {}
    for leg in legs:
        running = totals.setdefault(leg.currency, Decimal("0"))
        if leg.debit is not None:
            running += parse_money(leg.debit)
        if leg.credit is not None:
            running -= parse_money(leg.credit)
        totals[leg.currency] = running
    return totals


def check_balanced(legs: Sequence[Leg]) -> None:
    """Raise unless every currency sums to exactly zero.

    Compared as ``Decimal``, so there is no float tolerance to hide behind.
    """
    if not legs:
        raise UnbalancedError("a posting must have at least one leg")

    for currency, total in _totals(legs).items():
        if total != Decimal("0"):
            raise UnbalancedError(
                f"posting does not balance in {currency}: net {to_money_string(total, currency)}"
            )


def post(conn: db.Connection, run_id: str, legs: Sequence[Leg]) -> int:
    """Write one balanced posting to ``journal_line``. Returns the first line number.

    Validation happens before any write, so a rejected posting leaves no rows.
    """
    check_balanced(legs)

    row = conn.execute(
        "SELECT COALESCE(MAX(line_no), 0) AS n FROM journal_line WHERE run_id = ?", (run_id,)
    ).fetchone()
    first_line = int(row["n"]) + 1

    at = _now_iso()
    for offset, leg in enumerate(legs):
        conn.execute(
            "INSERT INTO journal_line"
            " (id, run_id, line_no, occurred_at, account, debit, credit, currency, source_id, memo)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"{run_id}:{first_line + offset}",
                run_id,
                first_line + offset,
                at,
                leg.account,
                leg.debit,
                leg.credit,
                leg.currency,
                leg.source_id,
                leg.memo,
            ),
        )
    return first_line


def balances(conn: db.Connection) -> dict[str, dict[str, Decimal]]:
    """Running debit and credit totals per currency across the whole ledger."""
    out: dict[str, dict[str, Decimal]] = {}
    for row in conn.execute("SELECT currency, debit, credit FROM journal_line"):
        bucket = out.setdefault(row["currency"], {"debit": Decimal("0"), "credit": Decimal("0")})
        if row["debit"] is not None:
            bucket["debit"] += parse_money(row["debit"])
        if row["credit"] is not None:
            bucket["credit"] += parse_money(row["credit"])
    return out


def net_by_account(conn: db.Connection, account: str) -> Decimal:
    """Debit-minus-credit for one account, in its single currency."""
    total = Decimal("0")
    for row in conn.execute("SELECT debit, credit FROM journal_line WHERE account = ?", (account,)):
        if row["debit"] is not None:
            total += parse_money(row["debit"])
        if row["credit"] is not None:
            total -= parse_money(row["credit"])
    return total


def account_prefix_totals(conn: db.Connection, prefix: str) -> dict[str, Decimal]:
    """Net totals for every account starting with ``prefix``, grouped by currency.

    Used by reconciliation, which reasons about families like ``Wallet:`` and
    ``AP-clearing:`` rather than individual accounts.
    """
    totals: dict[str, Decimal] = {}
    rows = conn.execute(
        "SELECT account, currency, debit, credit FROM journal_line WHERE account LIKE ? || '%'",
        (prefix,),
    )
    for row in rows:
        currency = str(row["currency"])
        running = totals.setdefault(currency, Decimal("0"))
        if row["debit"] is not None:
            running += parse_money(row["debit"])
        if row["credit"] is not None:
            running -= parse_money(row["credit"])
        totals[currency] = running
    return totals


def assert_ledger_balances(conn: db.Connection) -> None:
    """Every currency's debits must equal its credits.

    The invariant the property tests lean on. Raises
    :class:`UnbalancedError` naming the offending currency.
    """
    for currency, bucket in balances(conn).items():
        if bucket["debit"] != bucket["credit"]:
            raise UnbalancedError(
                f"ledger does not balance in {currency}: "
                f"debit {to_money_string(bucket['debit'], currency)} != "
                f"credit {to_money_string(bucket['credit'], currency)}"
            )


def export_csv(conn: db.Connection, run_id: str) -> str:
    """The generic journal CSV: ``date, account, debit, credit, currency,
    amount_usd, source_id, memo`` (§4.13).

    Deliberately not an accounting-software export format: there is no API for
    one, and pretending otherwise would be a claim we cannot support.
    """
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["date", "account", "debit", "credit", "currency", "amount_usd", "source_id", "memo"]
    )
    rows = conn.execute(
        "SELECT occurred_at, account, debit, credit, currency, amount_usd, source_id, memo"
        " FROM journal_line WHERE run_id = ? ORDER BY line_no",
        (run_id,),
    )
    for row in rows:
        writer.writerow(
            [
                row["occurred_at"],
                row["account"],
                row["debit"] or "",
                row["credit"] or "",
                row["currency"],
                row["amount_usd"] or "",
                row["source_id"] or "",
                row["memo"] or "",
            ]
        )
    return buffer.getvalue()


def journal_line_for_run(conn: db.Connection, run_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM journal_line WHERE run_id = ? ORDER BY line_no", (run_id,)
        )
    ]
