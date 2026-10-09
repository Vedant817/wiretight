"""The policy floor: 30 hard-coded rows that a policy file may only tighten.

FINAL.md §4.15. ``policy.yaml`` is not configuration, it is a request to be
allowed to do something, and this module decides whether the request is within
bounds.

Three properties make the floor a control rather than a suggestion:

1. **Direction is explicit per constraint.** A minimum (cooling-off) may only
   increase; a maximum (a cap, a band ceiling) may only decrease; a set
   (disqualifiers) may only grow. There is no row whose direction is inferred,
   and no row whose meaning depends on a comment.
2. **Every value §4.15 names is bounded.** Row 7 names three values, row 14
   names five. A row that checked only one of them was a hole: a red-team pass
   found ``t0.bank_details_unchanged_days: 0`` accepted, which would have let a
   payee whose bank details changed *yesterday* qualify for auto-pay. One
   :class:`Constraint` per named value, and T-27 is parametrised over
   constraints rather than rows.
3. **Unknown *and* missing keys are errors.** An unknown key is how a floor
   gets bypassed by an option nobody audited; a missing key is how a floor
   silently stops applying.

Adding a 31st control means adding a row, which makes T-27 fail until someone
writes the loosen attempt for it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Final

#: Appended to a violation that two valid approver signatures would clear.
#: §4.15 r10 makes T0 legal only under a signed policy, which is not expressible
#: as a plain bound because the floor cannot see the signature material.
REQUIRES_SIGNATURES_MARKER: Final[str] = " [requires two approver signatures]"

# ---------------------------------------------------------------------------
# A recursive description of the policy's shape.
# ---------------------------------------------------------------------------
MONEY = "money"  # a finite decimal string, never a YAML number
NUM = "num"  # a non-negative int
BOOL = "bool"  # a real YAML boolean
STR = "str"
FREEMAP = "freemap"  # a mapping whose keys are not enumerated (rail names, categories)

#: shape := leaf | [shape, ...] (a list) | {key: shape, ...} (a mapping)
Shape = str | list[Any] | dict[str, Any]

SCHEMA: dict[str, Any] = {
    "policy_version": STR,
    "entity_id": STR,
    "base_currency": STR,
    "reserve_floor": FREEMAP,
    "roster": [
        {"id": STR, "name": STR, "role": STR, "email": STR},
    ],
    "bank_change": {
        "cooling_off_hours": NUM,
        "callback_contact_min_age_days": NUM,
        "callback_validity_days": NUM,
        "contact_provenance_min_invoice_age_days": NUM,
        "first_payment_cap_usd": MONEY,
        "first_payment_cap_median_fraction": MONEY,
        "cap_lift_final_payments": NUM,
    },
    "t0": {
        "enabled": BOOL,
        "per_payment_limit_usd": MONEY,
        "min_final_payments": NUM,
        "min_payment_fraction_of_limit": MONEY,
        "bank_details_unchanged_days": NUM,
        "max_multiple_of_payee_median": MONEY,
        "disqualifiers": [STR],
    },
    "tiers": {
        "t2_threshold_usd": MONEY,
        "t2_payee_7d_aggregate_usd": MONEY,
    },
    "limits": {
        "per_run": {"t0_usd": MONEY, "all_usd": MONEY, "max_payments": NUM},
        "per_day": {
            "t0_usd": MONEY,
            "all_usd": MONEY,
            "max_payments": NUM,
            "max_runs": NUM,
            "max_new_beneficiaries": NUM,
            "calendar_tz": STR,
        },
        "per_payee_7d": {"t0_usd": MONEY},
        "per_payee_24h": {"max_t0": NUM, "max_payments": NUM},
        "per_approver_day_usd": MONEY,
    },
    "approvals": {"max_validity_hours": NUM, "challenge_ttl_seconds": NUM},
    "fx": {"quote_validity": STR, "quote_safety_margin_seconds": NUM, "drift_bp": NUM},
    "settlement": {
        "SEPA": {"business_days": NUM, "calendar": STR, "min_hours": NUM},
        "FPS": {"business_days": NUM, "calendar": STR, "min_hours": NUM},
        "ACH": {"business_days": NUM, "calendar": STR, "min_hours": NUM},
        "SWIFT": {"final_by_timer": BOOL, "presumed_settled_business_days": NUM},
    },
    "ambiguous": {"escalate_after_days": NUM},
    "killswitch": {
        "clock_skew_seconds": NUM,
        "ambiguous_creates_per_run": NUM,
        "ambiguous_creates_rolling_24h": NUM,
        "failed_transfers_rolling_1h": NUM,
        "extraction_conflicts_rolling_24h": NUM,
        "clear_signatures": NUM,
    },
    "rails": {
        "flight_business_days": FREEMAP,
        "cutoff_local_time": FREEMAP,
        "fee_reservation_usd": FREEMAP,
    },
    "vendor_category_reason": FREEMAP,
    "demo_timing": BOOL,
}

#: §4.15 row 3: contact provenance must come from an invoice at least this old.
MIN_CONTACT_PROVENANCE_INVOICE_AGE_DAYS = 90

#: Row 22, per rail. §4.15 states these three windows explicitly and they are NOT
#: uniform: SEPA 3 TARGET2 days, FPS 3 UK days, ACH 2 US days. A single minimum
#: of 3 rejected the spec's own shipped ACH value of 2.
SETTLE_FLOOR: dict[str, dict[str, int]] = {
    "SEPA": {"business_days": 3, "min_hours": 48},
    "FPS": {"business_days": 3, "min_hours": 48},
    "ACH": {"business_days": 2, "min_hours": 48},
}

#: Row 22: the 48 h absolute minimum applies to every rail that settles on a timer.
MIN_SETTLE_HOURS = 48

#: Every rail that must appear in ``settlement``. Omitting one means a transfer
#: on that rail has no settle window at all, which is fail-open (D-B14).
REQUIRED_SETTLEMENT_RAILS: frozenset[str] = frozenset({"SEPA", "FPS", "ACH", "SWIFT"})


class Direction(Enum):
    """How a value may move. Explicit per constraint; never inferred."""

    #: The value is a floor: it may only increase.
    MINIMUM = "minimum"
    #: The value is a ceiling: it may only decrease.
    MAXIMUM = "maximum"
    #: A set of flags: it may only grow.
    SUPERSET = "superset"
    #: An exact value that may not be changed at all.
    EXACT = "exact"


@dataclass(frozen=True)
class Constraint:
    """One bounded value.

    ``path`` is dotted. A path of ``""`` means "the whole section", used by rows
    whose check is structural (row 21's reserve floor, row 9's flag list).
    """

    path: str
    direction: Direction
    value: Any = None
    #: Rail name, for the per-rail rows.
    rail: str | None = None

    def where(self) -> str:
        base = f"{self.path}.{self.rail}" if self.rail else self.path
        return base or "<policy>"


@dataclass(frozen=True)
class FloorRow:
    """One of the 30 controls in §4.15.

    A row has as many constraints as §4.15 names values. Row 14 names five caps;
    checking one of them and calling the row covered was a hole found by review.
    """

    number: int
    control: str
    source: str
    constraints: tuple[Constraint, ...] = ()
    demo_override: str = "None"

    def describe(self) -> str:
        return f"r{self.number} ({self.control}) in FINAL.md {self.source}"


def _min(path: str, value: Any, rail: str | None = None) -> Constraint:
    return Constraint(path, Direction.MINIMUM, value, rail)


def _max(path: str, value: Any, rail: str | None = None) -> Constraint:
    return Constraint(path, Direction.MAXIMUM, value, rail)


def _exact(path: str, value: Any, rail: str | None = None) -> Constraint:
    return Constraint(path, Direction.EXACT, value, rail)


#: The floor. Shipped values are the loosest allowed (§4.15's column header).
FLOOR_ROWS: tuple[FloorRow, ...] = (
    FloorRow(
        1,
        "Cooling-off for new or changed details",
        "§4.15 r1 / §4.5.3",
        (_min("bank_change.cooling_off_hours", 72),),
        "2 min, only if AWX_ENV=sandbox + host pin + APP_DEMO_TIMING=true; labelled",
    ),
    FloorRow(
        2,
        "Callback contact age",
        "§4.15 r2 / §4.5.2",
        (_min("bank_change.callback_contact_min_age_days", 30),),
        "None (seed the fixture contact as old)",
    ),
    # Row 3 names three things: the validity window, the recorder rule (structural,
    # enforced in validate_shape) and the contact provenance age.
    FloorRow(
        3,
        "Callback validity, recorder and contact provenance",
        "§4.15 r3 / §4.5.2",
        (
            _max("bank_change.callback_validity_days", 7),
            _min(
                "bank_change.contact_provenance_min_invoice_age_days",
                MIN_CONTACT_PROVENANCE_INVOICE_AGE_DAYS,
            ),
        ),
        "None",
    ),
    FloorRow(
        4,
        "First-payment cap",
        "§4.15 r4 / §4.5.4",
        (
            _max("bank_change.first_payment_cap_usd", "2500.00"),
            _max("bank_change.first_payment_cap_median_fraction", "0.50"),
        ),
        "None",
    ),
    FloorRow(5, "Cap lift", "§4.15 r5", (_min("bank_change.cap_lift_final_payments", 2),), "None"),
    FloorRow(
        6,
        "T0 per-payment limit",
        "§4.15 r6",
        (_max("t0.per_payment_limit_usd", "2000.00"),),
        "None",
    ),
    # Row 7 names three: the count, the fraction of the limit, and how long the
    # bank details must be unchanged. Only the count was checked before.
    FloorRow(
        7,
        "T0 history",
        "§4.15 r7",
        (
            _min("t0.min_final_payments", 3),
            _min("t0.min_payment_fraction_of_limit", "0.25"),
            _min("t0.bank_details_unchanged_days", 60),
        ),
        "None (history seeded and labelled)",
    ),
    FloorRow(
        8, "T0 amount band", "§4.15 r8", (_max("t0.max_multiple_of_payee_median", "1.5"),), "None"
    ),
    FloorRow(
        9,
        "T0 disqualifiers",
        "§4.15 r9",
        (
            Constraint(
                "t0.disqualifiers",
                Direction.SUPERSET,
                [
                    "duplicate_suspicion",
                    "EXTRACTION_CONFLICT",
                    "HIDDEN_TEXT",
                    "new_country",
                    "contact_lt_30d",
                    "unknown_sender",
                    "SWIFT",
                    "degraded_check",
                    "cap_headroom",
                ],
            ),
        ),
        "None",
    ),
    FloorRow(
        10,
        "T0 enabled by default",
        "§4.15 r10",
        (_exact("t0.enabled", False),),
        "policy.demo.yaml turns it on, signed, labelled",
    ),
    # Rows 11 and 12. Both name the boundary below which ONE sign-off is enough.
    # That boundary is a CEILING: raising it would let a USD 400,000 payment
    # fall under it and get T1 instead of T2. (D-B11, corrected.)
    FloorRow(
        11,
        "T1 band ceiling (below which one sign-off suffices)",
        "§4.15 r11",
        (_max("tiers.t2_threshold_usd", "10000.00"),),
        "None",
    ),
    FloorRow(
        12,
        "T2 payee 7-day aggregate threshold",
        "§4.15 r12",
        (_max("tiers.t2_payee_7d_aggregate_usd", "10000.00"),),
        "None",
    ),
    FloorRow(
        13,
        "Per-run caps",
        "§4.15 r13",
        (
            _max("limits.per_run.t0_usd", "6000.00"),
            _max("limits.per_run.all_usd", "50000.00"),
            _max("limits.per_run.max_payments", 40),
        ),
        "None",
    ),
    FloorRow(
        14,
        "Per-day caps",
        "§4.15 r14",
        (
            _max("limits.per_day.t0_usd", "6000.00"),
            _max("limits.per_day.all_usd", "75000.00"),
            _max("limits.per_day.max_payments", 60),
            _max("limits.per_day.max_runs", 2),
            _max("limits.per_day.max_new_beneficiaries", 5),
        ),
        "None",
    ),
    FloorRow(
        15,
        "Per-payee rolling 7 days",
        "§4.15 r15",
        (_max("limits.per_payee_7d.t0_usd", "2000.00"),),
        "None",
    ),
    FloorRow(
        16,
        "Per-payee 24 h velocity",
        "§4.15 r16",
        (
            _max("limits.per_payee_24h.max_t0", 1),
            _max("limits.per_payee_24h.max_payments", 3),
        ),
        "None",
    ),
    FloorRow(
        17,
        "Per-approver daily total",
        "§4.15 r17",
        (_max("limits.per_approver_day_usd", "30000.00"),),
        "None",
    ),
    FloorRow(
        18,
        "Approval expiry and challenge",
        "§4.15 r18",
        (
            _max("approvals.max_validity_hours", 4),
            _max("approvals.challenge_ttl_seconds", 300),
        ),
        "None",
    ),
    FloorRow(
        19,
        "Quote safety margin",
        "§4.15 r19",
        (_min("fx.quote_safety_margin_seconds", 120),),
        "None",
    ),
    FloorRow(20, "FX drift tolerance", "§4.15 r20", (_max("fx.drift_bp", 25),), "None"),
    FloorRow(
        21,
        "Reserve floor",
        "§4.15 r21",
        (Constraint("reserve_floor", Direction.MINIMUM, {"USD": "8000.00"}),),
        "missing -> executor refuses to start",
    ),
    FloorRow(
        22,
        "Settle window (PAID to FINAL)",
        "§4.15 r22",
        tuple(
            _min(f"settlement.{rail}.min_hours", MIN_SETTLE_HOURS)
            # SWIFT is excluded on purpose: it is never FINAL by timer, so
            # it has no min_hours. It is bounded instead by requiring
            # final_by_timer: false and a >= 10-business-day presumed window,
            # checked in _check_settlement.
            for rail in sorted(set(SETTLE_FLOOR))
        ),
        "not used (FINAL is never shortened)",
    ),
    FloorRow(
        23, "AMBIGUOUS escalation", "§4.15 r23", (_min("ambiguous.escalate_after_days", 6),), "None"
    ),
    FloorRow(
        24, "Trip: clock skew", "§4.15 r24", (_max("killswitch.clock_skew_seconds", 120),), "None"
    ),
    # Row 25's demo-visible knob is the SEPA fee *reservation*, a MINIMUM: reducing
    # it would let the planner promise a reserve the wallet does not hold.
    FloorRow(
        25,
        "Trip on first occurrence",
        "§4.15 r25",
        tuple(
            _min(f"rails.fee_reservation_usd.{rail}", value)
            for rail, value in (
                ("SEPA", "5.00"),
                ("FPS", "5.00"),
                ("ACH", "5.00"),
                ("SWIFT", "30.00"),
            )
        ),
        "None",
    ),
    FloorRow(
        26,
        "Trip: AMBIGUOUS creates",
        "§4.15 r26",
        (
            _max("killswitch.ambiguous_creates_per_run", 2),
            _max("killswitch.ambiguous_creates_rolling_24h", 2),
        ),
        "None",
    ),
    FloorRow(
        27,
        "Trip: FAILED transfers",
        "§4.15 r27",
        (_max("killswitch.failed_transfers_rolling_1h", 3),),
        "None",
    ),
    FloorRow(
        28,
        "LLM vs parser identifier mismatch",
        "§4.15 r28",
        (_max("killswitch.extraction_conflicts_rolling_24h", 3),),
        "None",
    ),
    # Row 29: never shorten a rail's flight time.
    FloorRow(
        29,
        "Trip on first occurrence (added)",
        "§4.15 r29",
        tuple(
            _min(f"rails.flight_business_days.{rail}", value)
            for rail, value in (("SEPA", 2), ("FPS", 1), ("ACH", 2), ("SWIFT", 3))
        ),
        "None",
    ),
    FloorRow(
        30,
        "Clearing the kill switch",
        "§4.15 r30",
        (_min("killswitch.clear_signatures", 2),),
        "None",
    ),
)

#: Every rail whose flight time row 29 protects.
ALL_RAILS: tuple[str, ...] = ("SEPA", "FPS", "ACH", "SWIFT")


@dataclass
class FloorResult:
    """Outcome of checking a policy against the floor."""

    ok: bool
    violations: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _get(policy: Mapping[str, Any], dotted: str) -> Any:
    current: Any = policy
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _violation(row: FloorRow, detail: str) -> str:
    return f"{row.describe()}: {detail}"


def to_decimal(value: Any) -> Decimal | None:
    """Parse a policy money value, refusing anything not finite.

    ``Decimal("Infinity")`` and ``Decimal("NaN")`` both parse, and both defeat a
    naive bound: ``Infinity < 10000`` is False, so a MINIMUM row would accept it
    and no payment would ever escalate to T2. Returns ``None`` instead of raising
    so the caller reports a violation rather than crashing the loader.
    """
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


# ---------------------------------------------------------------------------
# Per-constraint checks
# ---------------------------------------------------------------------------
def _check_reserve_floor(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Row 21: the floor must be set at all, and never below the shipped value."""
    floor = policy.get("reserve_floor")
    if not isinstance(floor, Mapping) or not floor:
        return [_violation(row, "reserve_floor is missing; the executor would refuse to start")]

    shipped = row.constraints[0].value or {}
    problems: list[str] = []
    for currency, value in floor.items():
        actual = to_decimal(value)
        if actual is None:
            problems.append(
                _violation(row, f"{currency} floor {value!r} is not a finite decimal string")
            )
            continue
        if actual < 0:
            problems.append(_violation(row, f"{currency} floor is negative"))
            continue
        reference = to_decimal(shipped.get(currency)) if isinstance(shipped, Mapping) else None
        if reference is not None and actual < reference:
            problems.append(
                _violation(row, f"{currency} floor {value} is below the floor {shipped[currency]}")
            )
    return problems


def _check_settlement(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Row 22: PAID -> FINAL must be at least 48 h and at least the rail's window.

    Every required rail must be *present*. A policy that omitted SEPA used to
    pass, which left SEPA transfers with no settle window at all — fail-open on
    the row that stops us declaring money settled when it is not.
    """
    settlement = policy.get("settlement")
    if not isinstance(settlement, Mapping):
        return [_violation(row, "settlement block is missing")]

    problems: list[str] = []
    for rail in sorted(REQUIRED_SETTLEMENT_RAILS):
        if rail not in settlement:
            problems.append(
                _violation(row, f"settlement.{rail} is missing; that rail would have no window")
            )
    for rail in sorted(set(settlement) - REQUIRED_SETTLEMENT_RAILS):
        problems.append(_violation(row, f"settlement.{rail} is not a rail Wiretight pays on"))

    for rail in sorted(REQUIRED_SETTLEMENT_RAILS):
        spec = settlement.get(rail)
        if not isinstance(spec, Mapping):
            continue
        if rail == "SWIFT":
            if spec.get("final_by_timer") is not False:
                problems.append(_violation(row, "SWIFT must set final_by_timer: false"))
            days = spec.get("presumed_settled_business_days")
            if isinstance(days, bool) or not isinstance(days, int) or days < 10:
                problems.append(
                    _violation(
                        row, f"SWIFT.presumed_settled_business_days is {days!r}, floor is 10"
                    )
                )
            continue

        floor = SETTLE_FLOOR[rail]
        hours = spec.get("min_hours")
        if isinstance(hours, bool) or not isinstance(hours, int):
            problems.append(_violation(row, f"{rail}.min_hours is {hours!r}, not an integer"))
        elif hours < MIN_SETTLE_HOURS:
            problems.append(
                _violation(row, f"{rail}.min_hours is {hours}, floor is {MIN_SETTLE_HOURS}")
            )

        days = spec.get("business_days")
        if isinstance(days, bool) or not isinstance(days, int):
            problems.append(_violation(row, f"{rail}.business_days is {days!r}, not an integer"))
        elif days < floor["business_days"]:
            problems.append(
                _violation(
                    row, f"{rail}.business_days is {days}, floor is {floor['business_days']}"
                )
            )
    return problems


def check_settle_window_conjunction(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """§4.15 r22 requires the window to satisfy **both** bounds.

    FINAL.md reads "≥ 48 h **and** ≥ the rail's business-day window". Checking the
    two numbers independently lets a policy set ``business_days: 30`` beside
    ``min_hours: 48``, and ``min_hours`` is the number the poller actually
    consults via ``wt_next(final_due=...)`` — so the effective window would be
    two days while the policy *reads* as thirty (measured, D-B20).

    Not modelled as a ``Constraint`` because the two numbers cannot be compared
    without both being visible, and T-27's parametrisation sets one value at a
    time. It lives here, beside the per-rail loop, and the shipped example passes
    because 48 h is under three banking days but the row it belongs to is the
    *day count*.
    """
    settlement = policy.get("settlement")
    if not isinstance(settlement, Mapping):
        return []

    problems: list[str] = []
    for rail, floor in SETTLE_FLOOR.items():
        spec = settlement.get(rail)
        if not isinstance(spec, Mapping):
            continue
        hours = spec.get("min_hours")
        days = spec.get("business_days")
        if (
            isinstance(hours, bool)
            or not isinstance(hours, int)
            or isinstance(days, bool)
            or not isinstance(days, int)
        ):
            continue
        # Only binds once the policy asks for more days than the shipped floor.
        if days <= floor["business_days"]:
            continue
        if hours < days * _HOURS_PER_BANKING_DAY:
            problems.append(
                _violation(
                    row,
                    f"{rail}: min_hours {hours} is shorter than the {days} business days "
                    f"this policy requests (at least {days * _HOURS_PER_BANKING_DAY} h). "
                    "min_hours is what the poller uses, so the effective window would "
                    "be {hours} h, not {days} days. FINAL.md §4.15 r22 requires both.",
                )
            )
    return problems


#: Assumed length of one banking day for the r22 conjunction. An over-estimate,
#: deliberately: a TARGET2 day is not 24 h once weekends and TARGET2 closing days
#: intervene, so this makes the check stricter than reality. The actual FINAL time
#: comes from the committed calendar, never from this.
_HOURS_PER_BANKING_DAY: Final[int] = 24


def _check_superset(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Row 9: the disqualifier list may only grow."""
    constraint = row.constraints[0]
    actual = _get(policy, constraint.path)
    if not isinstance(actual, list):
        return [_violation(row, f"{constraint.where()} is {type(actual).__name__}, not a list")]
    required = [flag for flag in (constraint.value or []) if flag not in actual]
    if required:
        return [_violation(row, f"{constraint.where()} dropped {', '.join(required)}")]
    return []


def _check_exact(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Row 10: T0 must be a real boolean, and Off unless signatures authorise it.

    The type check was the whole implementation, and ``constraint.value`` — the
    ``False`` this row ships — was never consulted, so ``t0.enabled: true`` passed
    a row whose value is ``False`` (measured, D-B20).

    §4.15 r10 makes T0 legal *only* under a two-signature policy, and that is not
    expressible as a plain bound because it depends on material the floor does not
    see. So this returns a violation carrying ``requires_signatures=True`` rather
    than a hard refusal: :func:`check_policy_against_floor` treats it as a
    violation, and :func:`app.core.policy.load_policy` clears it only when the
    signature file verified. The result is that ``allow_unsigned=True`` can no
    longer reach live auto-payout, which it could before.
    """
    constraint = row.constraints[0]
    value = _get(policy, constraint.path)
    if not isinstance(value, bool):
        return [_violation(row, f"{constraint.where()} is {value!r}, not a boolean")]
    if value != constraint.value:
        message = _violation(
            row,
            f"{constraint.where()} is {value!r}; the shipped floor is "
            f"{constraint.value!r}. Turning auto-pay on is permitted only by a "
            "policy carrying two distinct approver signatures "
            "(FINAL.md §4.15 r10, §6.4) — see policy.demo.yaml",
        )
        # load_policy() looks for this to decide whether signatures clear it.
        return [f"{message}{REQUIRES_SIGNATURES_MARKER}"]
    return []


def _only_signature_gated(violations: Sequence[str]) -> list[str]:
    """The violations that two valid signatures would clear."""
    return [v for v in violations if v.endswith(REQUIRES_SIGNATURES_MARKER)]


def without_signature_gated(violations: Sequence[str]) -> list[str]:
    """Drop the signature-gated violations, leaving the hard ones.

    Used by :func:`app.core.policy.load_policy` after signatures have verified.
    """
    return [v[: -len(REQUIRES_SIGNATURES_MARKER)] for v in _only_signature_gated(violations)]


def has_signature_gated_violation(violations: Sequence[str]) -> bool:
    """Does this result depend on T0 being turned on without signatures?"""
    return bool(_only_signature_gated(violations))


def check_constraint(row: FloorRow, constraint: Constraint, policy: Mapping[str, Any]) -> list[str]:
    """Return the violations for one constraint. An empty list means it holds.

    MONEY floors also reject negative values. Only ``_check_reserve_floor`` had
    that guard, so ``first_payment_cap_usd: -2500`` — which makes tranche 1 a
    negative payment — and ``per_approver_day_usd: -30000`` — which stops row 17
    binding at all — both passed every MONEY row (measured, D-B20).
    """
    if row.number == 21:
        return _check_reserve_floor(row, policy)
    if row.number == 22:
        return _check_settlement(row, policy)
    if constraint.direction is Direction.SUPERSET:
        return _check_superset(row, policy)
    if constraint.direction is Direction.EXACT:
        return _check_exact(row, policy)

    actual_raw = _get(policy, constraint.where())

    # Money-shaped floors compare as Decimal.
    if isinstance(constraint.value, str):
        expected = to_decimal(constraint.value)
        actual = to_decimal(actual_raw)
        if actual is None:
            return [
                _violation(
                    row,
                    f"{constraint.where()} is {actual_raw!r}, not a finite decimal string"
                    " (a float, NaN or Infinity would defeat this bound)",
                )
            ]
        assert expected is not None
        if actual < 0:
            return [
                _violation(
                    row,
                    f"{constraint.where()} is negative ({actual_raw}); a negative "
                    "limit inverts the control it is meant to bound",
                )
            ]
        if constraint.direction is Direction.MINIMUM and actual < expected:
            return [
                _violation(
                    row, f"{constraint.where()} is {actual_raw}, floor is {constraint.value}"
                )
            ]
        if constraint.direction is Direction.MAXIMUM and actual > expected:
            return [
                _violation(
                    row, f"{constraint.where()} is {actual_raw}, ceiling is {constraint.value}"
                )
            ]
        return []

    if isinstance(constraint.value, int) and not isinstance(constraint.value, bool):
        if isinstance(actual_raw, bool) or not isinstance(actual_raw, int):
            return [_violation(row, f"{constraint.where()} is {actual_raw!r}, not an integer")]
        if constraint.direction is Direction.MINIMUM and actual_raw < constraint.value:
            return [
                _violation(
                    row, f"{constraint.where()} is {actual_raw}, floor is {constraint.value}"
                )
            ]
        if constraint.direction is Direction.MAXIMUM and actual_raw > constraint.value:
            return [
                _violation(
                    row, f"{constraint.where()} is {actual_raw}, ceiling is {constraint.value}"
                )
            ]
        return []

    return []


def check_row(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Every violation for one row, across all of its constraints."""
    violations: list[str] = []
    if row.number == 22:
        violations.extend(check_settle_window_conjunction(row, policy))
    for constraint in row.constraints:
        violations.extend(check_constraint(row, constraint, policy))
    return violations


def check_policy_against_floor(policy: Mapping[str, Any]) -> FloorResult:
    """Check every row. Returns all violations, not just the first."""
    violations: list[str] = []
    for row in FLOOR_ROWS:
        violations.extend(check_row(row, policy))
    return FloorResult(ok=not violations, violations=violations)


def all_constraints() -> list[tuple[FloorRow, Constraint]]:
    """Every (row, constraint) pair, for T-27's parametrisation."""
    return [(row, constraint) for row in FLOOR_ROWS for constraint in row.constraints]


# ---------------------------------------------------------------------------
# Shape validation: unknown keys, missing keys, wrong types
# ---------------------------------------------------------------------------
def _row_for(path: str) -> int | None:
    """The floor row a path belongs to, matched on the longest known prefix.

    Needed because the per-rail constraints live at paths like
    ``settlement.SEPA.min_hours``, and an exact-match lookup would leave the
    operator with no indication which row they had just attempted to loosen.
    """
    if path in PATH_TO_ROW:
        return PATH_TO_ROW[path]
    parts = path.split(".")
    for length in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:length])
        if prefix in PATH_TO_ROW:
            return PATH_TO_ROW[prefix]
    return None


def _missing_key(path: str) -> str:
    row = _row_for(path)
    suffix = f" (FINAL.md §4.15 r{row})" if row else ""
    return f"missing key {path} (FINAL.md §4.15){suffix}"


def _check_shape_at(value: Any, shape: Shape, path: str, problems: list[str]) -> None:
    """Recursively compare one value against its declared shape.

    Reports every unknown key, missing key and type mismatch rather than
    stopping at the first: an operator fixing a policy file needs the whole list.
    """
    if shape is FREEMAP:
        if not isinstance(value, Mapping):
            problems.append(f"{path} must be a mapping, got {type(value).__name__}")
            return
        for key, item in value.items():
            if not isinstance(key, str):
                problems.append(f"{path} has a non-string key {key!r}")
            elif isinstance(item, bool):
                problems.append(f"{path}.{key} must be a decimal string, not a bool")
        return

    if isinstance(shape, list):
        if not isinstance(value, list):
            problems.append(f"{path} must be a list, got {type(value).__name__}")
            return
        for index, item in enumerate(value):
            if shape:
                _check_shape_at(item, shape[0], f"{path}[{index}]", problems)
        return

    if isinstance(shape, dict):
        if not isinstance(value, Mapping):
            problems.append(f"{path} must be a mapping, got {type(value).__name__}")
            return
        for key in value:
            if key not in shape:
                problems.append(f"unknown key {f'{path}.' if path else ''}{key!r} (FINAL.md §4.15)")
        for key, child in shape.items():
            child_path = f"{path}.{key}" if path else key
            if key not in value:
                problems.append(_missing_key(child_path))
                continue
            _check_shape_at(value[key], child, child_path, problems)
        return

    if shape == MONEY:
        row = _row_for(path)
        suffix = f" (FINAL.md §4.15 r{row})" if row else ""
        if isinstance(value, bool):
            problems.append(f"{path} must be a decimal string, not a bool{suffix}")
        elif isinstance(value, (int, float)):
            problems.append(
                f"{path} must be a decimal string, not a {type(value).__name__}{suffix}: "
                "a float is not a signed amount (FINAL.md §7.3)"
            )
        elif not isinstance(value, str):
            problems.append(f"{path} must be a decimal string, got {type(value).__name__}{suffix}")
        elif value.strip() != value or not value:
            problems.append(f"{path} is not a clean decimal string: {value!r}{suffix}")
        elif to_decimal(value) is None:
            problems.append(
                f"{path} is not a finite decimal: {value!r}{suffix} "
                "(NaN and Infinity defeat every numeric bound)"
            )
        return

    if shape == NUM:
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"{path} must be an integer, got {value!r}")
        elif value < 0:
            problems.append(f"{path} must not be negative, got {value}")
        return

    if shape == BOOL:
        if not isinstance(value, bool):
            row = _row_for(path)
            suffix = f" (FINAL.md §4.15 r{row})" if row else ""
            problems.append(f"{path} must be a boolean, got {value!r}{suffix}")
        return

    if not isinstance(value, str):
        problems.append(f"{path} must be a string, got {type(value).__name__}")


#: Reverse index, so a structural error names the floor row it offends. Without
#: it, "t0.enabled must be a boolean" is a confusing way to learn you have just
#: attempted to loosen r10.
PATH_TO_ROW: dict[str, int] = {
    "bank_change.cooling_off_hours": 1,
    "bank_change.callback_contact_min_age_days": 2,
    "bank_change.callback_validity_days": 3,
    "bank_change.contact_provenance_min_invoice_age_days": 3,
    "bank_change.first_payment_cap_usd": 4,
    "bank_change.first_payment_cap_median_fraction": 4,
    "bank_change.cap_lift_final_payments": 5,
    "t0.per_payment_limit_usd": 6,
    "t0.min_final_payments": 7,
    "t0.min_payment_fraction_of_limit": 7,
    "t0.bank_details_unchanged_days": 7,
    "t0.max_multiple_of_payee_median": 8,
    "t0.disqualifiers": 9,
    "t0.enabled": 10,
    "tiers.t2_threshold_usd": 11,
    "tiers.t2_payee_7d_aggregate_usd": 12,
    "limits.per_run": 13,
    "limits.per_day": 14,
    "limits.per_payee_7d": 15,
    "limits.per_payee_24h": 16,
    "limits.per_approver_day_usd": 17,
    "approvals": 18,
    "fx.quote_safety_margin_seconds": 19,
    "fx.drift_bp": 20,
    "reserve_floor": 21,
    "settlement": 22,
    "ambiguous.escalate_after_days": 23,
    "killswitch.clock_skew_seconds": 24,
    "killswitch.ambiguous_creates_per_run": 26,
    "killswitch.ambiguous_creates_rolling_24h": 26,
    "killswitch.failed_transfers_rolling_1h": 27,
    "killswitch.extraction_conflicts_rolling_24h": 28,
    "killswitch.clear_signatures": 30,
}


def _check_roster(policy: Mapping[str, Any]) -> list[str]:
    """Unique emails, a known role, and enough approvers for T2 (D6, §4.8).

    A roster with fewer than three approvers is not a load error: §4.4 makes
    every T2 item ``INSUFFICIENT_APPROVERS`` while the kill switch can still be
    cleared by two. That is a runtime HOLD, not a bad configuration, so it is
    deliberately not refused here.
    """
    problems: list[str] = []
    roster = policy.get("roster")
    if not isinstance(roster, list) or not roster:
        return ["roster is missing or empty"]

    seen: set[str] = set()
    for entry in roster:
        if not isinstance(entry, Mapping):
            problems.append(f"roster entry {entry!r} is not a mapping")
            continue
        email = entry.get("email")
        if not isinstance(email, str):
            problems.append(f"roster entry {entry.get('id')!r} has no email string")
            continue
        lowered = email.strip().lower()
        if lowered in seen:
            problems.append(f"duplicate roster email {email!r}; emails must be unique")
        seen.add(lowered)
        if entry.get("role") not in {"approver", "ops"}:
            problems.append(f"roster entry {entry.get('id')!r} has role {entry.get('role')!r}")
    return problems


def validate_shape(policy: Mapping[str, Any]) -> list[str]:
    """All structural problems: unknown keys, missing keys, wrong types, roster."""
    problems: list[str] = []
    for key in policy:
        if key not in SCHEMA:
            problems.append(
                f"unknown top-level key {key!r} (FINAL.md §4.15: an unknown key is a load error)"
            )
    for key, shape in SCHEMA.items():
        if key not in policy:
            problems.append(_missing_key(key))
            continue
        _check_shape_at(policy[key], shape, key, problems)
    return [*problems, *_check_roster(policy)]
