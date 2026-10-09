"""The policy floor: 30 hard-coded rows that a policy file may only tighten.

FINAL.md §4.15. ``policy.yaml`` is not configuration, it is a request to be
allowed to do something, and this module decides whether the request is within
bounds.

Three properties make the floor a control rather than a suggestion:

1. **Direction is explicit per row.** A minimum (cooling-off) may only go up; a
   maximum (a cap) may only go down; a set (disqualifiers) may only grow. There
   is no row whose direction is inferred.
2. **Unknown keys are errors.** ``duplicates.enabled`` and ``skip_callback``
   are named in §4.15 precisely because an unknown key is how a floor gets
   quietly bypassed by an option nobody audited.
3. **The rows are data, not code paths.** A 31st control is a new
   :class:`FloorRow`, and T-27's parametrised test then *fails* until someone
   writes the loosen attempt for it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# A recursive description of the policy's shape.
# ---------------------------------------------------------------------------
#: Leaves. Anything not reachable in this tree is an unknown key, and an unknown
#: key is a load error (§4.15). That is the whole point: an unaudited option is
#: a way to bypass a floor row nobody looked at.
MONEY = "money"  # a decimal string, never a YAML number
NUM = "num"  # an int
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
        {
            "id": STR,
            "name": STR,
            "role": STR,
            "email": STR,
        }
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

#: §4.15 row 3: contact provenance must be at least this old, in days.
MIN_CONTACT_PROVENANCE_INVOICE_AGE_DAYS = 90

#: Row 22, per rail. §4.15 states these three windows explicitly and they are
#: NOT uniform: SEPA 3 TARGET2 days, FPS 3 UK days, ACH 2 US days. A single
#: minimum of 3 would reject the spec's own shipped ACH value.
SETTLE_FLOOR: dict[str, dict[str, int]] = {
    "SEPA": {"business_days": 3, "min_hours": 48},
    "FPS": {"business_days": 3, "min_hours": 48},
    "ACH": {"business_days": 2, "min_hours": 48},
}

#: Row 22: the 48 h absolute minimum applies to every rail that settles on a timer.
MIN_SETTLE_HOURS = 48


class Direction(Enum):
    """How a row may move. Explicit per row; never inferred."""

    #: The value is a floor: it may only increase.
    MINIMUM = "minimum"
    #: The value is a ceiling: it may only decrease.
    MAXIMUM = "maximum"
    #: A set of flags: it may only grow.
    SUPERSET = "superset"


@dataclass(frozen=True)
class FloorRow:
    """One of the 30 controls in §4.15.

    ``path`` is the dotted key into the policy mapping. ``check`` is the actual
    comparison, so a row can express rules that are not a plain bound (row 9's
    disqualifier list, row 21's "must be set").
    """

    number: int
    control: str
    source: str
    direction: Direction
    floor_value: Any = None
    path: str | None = None
    demo_override: str = "None"

    def describe(self) -> str:
        return f"r{self.number} ({self.control})"


#: The floor. Shipped values are the loosest allowed (§4.15).
FLOOR_ROWS: tuple[FloorRow, ...] = (
    FloorRow(
        1,
        "Cooling-off for new or changed details",
        "§4.15 r1 / §4.5.3",
        Direction.MINIMUM,
        72,
        "bank_change.cooling_off_hours",
        "2 min, only if AWX_ENV=sandbox + host pin + APP_DEMO_TIMING=true; labelled",
    ),
    FloorRow(
        2,
        "Callback contact age",
        "§4.15 r2 / §4.5.2",
        Direction.MINIMUM,
        30,
        "bank_change.callback_contact_min_age_days",
        "None (seed the fixture contact as old)",
    ),
    # A callback is only evidence if it happened recently, so r3 is a MAXIMUM:
    # a 90-day window would let a stale confirmation release a new bank detail.
    FloorRow(
        3,
        "Callback validity and recorder",
        "§4.15 r3 / §4.5.2",
        Direction.MAXIMUM,
        7,
        "bank_change.callback_validity_days",
        "None",
    ),
    FloorRow(
        4,
        "First-payment cap",
        "§4.15 r4 / §4.5.4",
        Direction.MAXIMUM,
        "2500.00",
        "bank_change.first_payment_cap_usd",
        "None",
    ),
    FloorRow(
        5,
        "Cap lift",
        "§4.15 r5",
        Direction.MINIMUM,
        2,
        "bank_change.cap_lift_final_payments",
        "None",
    ),
    FloorRow(
        6,
        "T0 per-payment limit",
        "§4.15 r6",
        Direction.MAXIMUM,
        "2000.00",
        "t0.per_payment_limit_usd",
        "None",
    ),
    FloorRow(
        7,
        "T0 history",
        "§4.15 r7",
        Direction.MINIMUM,
        3,
        "t0.min_final_payments",
        "None (history seeded and labelled)",
    ),
    FloorRow(
        8,
        "T0 amount band",
        "§4.15 r8",
        Direction.MAXIMUM,
        "1.5",
        "t0.max_multiple_of_payee_median",
        "None",
    ),
    FloorRow(
        9,
        "T0 disqualifiers",
        "§4.15 r9",
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
        "t0.disqualifiers",
        "None",
    ),
    FloorRow(
        10,
        "T0 enabled by default",
        "§4.15 r10",
        Direction.MINIMUM,
        False,
        "t0.enabled",
        "policy.demo.yaml turns it on, signed, labelled",
    ),
    # Rows 11 and 12 both constrain `tiers.t2_threshold_usd`, which §4.15 lists as
    # ">= USD 10,000" in a column headed "Shipped value (loosest allowed)". The
    # direction is therefore MINIMUM: 10,000 is the loosest permitted value and a
    # policy may only raise it.
    #
    # Note this is the opposite of what intuition suggests: raising the threshold
    # sends *more* items to two sign-offs, which is stricter. The shipped policy
    # already uses 10000 for both rows 11 and 12, so one row's direction must
    # give; MINIMUM is the reading §4.15's own column header supports.
    FloorRow(
        11,
        "T1 band (T1/T2 boundary; may only be raised)",
        "§4.15 r11",
        Direction.MINIMUM,
        "10000.00",
        "tiers.t2_threshold_usd",
        "None",
    ),
    FloorRow(
        12,
        "T2 payee 7-day aggregate threshold",
        "§4.15 r12",
        Direction.MINIMUM,
        "10000.00",
        "tiers.t2_payee_7d_aggregate_usd",
        "None",
    ),
    FloorRow(
        13,
        "Per-run caps",
        "§4.15 r13",
        Direction.MAXIMUM,
        "6000.00",
        "limits.per_run.t0_usd",
        "None",
    ),
    FloorRow(
        14,
        "Per-day caps",
        "§4.15 r14",
        Direction.MAXIMUM,
        "75000.00",
        "limits.per_day.all_usd",
        "None",
    ),
    FloorRow(
        15,
        "Per-payee rolling 7 days",
        "§4.15 r15",
        Direction.MAXIMUM,
        "2000.00",
        "limits.per_payee_7d.t0_usd",
        "None",
    ),
    FloorRow(
        16,
        "Per-payee 24 h velocity",
        "§4.15 r16",
        Direction.MAXIMUM,
        3,
        "limits.per_payee_24h.max_payments",
        "None",
    ),
    FloorRow(
        17,
        "Per-approver daily total",
        "§4.15 r17",
        Direction.MAXIMUM,
        "30000.00",
        "limits.per_approver_day_usd",
        "None",
    ),
    FloorRow(
        18,
        "Approval expiry and challenge",
        "§4.15 r18",
        Direction.MAXIMUM,
        4,
        "approvals.max_validity_hours",
        "None",
    ),
    FloorRow(
        19,
        "Quote safety margin",
        "§4.15 r19",
        Direction.MINIMUM,
        120,
        "fx.quote_safety_margin_seconds",
        "None",
    ),
    FloorRow(20, "FX drift tolerance", "§4.15 r20", Direction.MAXIMUM, 25, "fx.drift_bp", "None"),
    FloorRow(
        21,
        "Reserve floor",
        "§4.15 r21",
        Direction.MINIMUM,
        {"USD": "8000.00"},
        "reserve_floor",
        "missing -> executor refuses to start",
    ),
    FloorRow(
        22,
        "Settle window (PAID to FINAL)",
        "§4.15 r22",
        Direction.MINIMUM,
        SETTLE_FLOOR,
        "settlement",
        "not used (FINAL is never shortened)",
    ),
    FloorRow(
        23,
        "AMBIGUOUS escalation",
        "§4.15 r23",
        Direction.MINIMUM,
        6,
        "ambiguous.escalate_after_days",
        "None",
    ),
    FloorRow(
        24,
        "Trip: clock skew",
        "§4.15 r24",
        Direction.MAXIMUM,
        120,
        "killswitch.clock_skew_seconds",
        "None",
    ),
    FloorRow(
        25,
        "Trip on first occurrence",
        "§4.15 r25",
        Direction.MINIMUM,
        "5.00",
        "rails.fee_reservation_usd.SEPA",
        "None",
    ),
    FloorRow(
        26,
        "Trip: AMBIGUOUS creates",
        "§4.15 r26",
        Direction.MAXIMUM,
        2,
        "killswitch.ambiguous_creates_per_run",
        "None",
    ),
    FloorRow(
        27,
        "Trip: FAILED transfers",
        "§4.15 r27",
        Direction.MAXIMUM,
        3,
        "killswitch.failed_transfers_rolling_1h",
        "None",
    ),
    FloorRow(
        28,
        "LLM vs parser identifier mismatch",
        "§4.15 r28",
        Direction.MAXIMUM,
        3,
        "killswitch.extraction_conflicts_rolling_24h",
        "None",
    ),
    FloorRow(
        29,
        "Trip on first occurrence (added)",
        "§4.15 r29",
        Direction.MINIMUM,
        1,
        "rails.flight_business_days.SEPA",
        "None",
    ),
    FloorRow(
        30,
        "Clearing the kill switch",
        "§4.15 r30",
        Direction.MINIMUM,
        2,
        "killswitch.clear_signatures",
        "None",
    ),
)

#: Rows whose check is not expressible as a single dotted path, handled by name.
SPECIAL_ROWS: frozenset[int] = frozenset({9, 10, 21, 22})


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


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise InvalidOperation("bool is not a number")
    if isinstance(value, (int, float)):
        # A bare YAML number in a money field is refused upstream. Reaching here
        # with one would mean the type check was skipped.
        raise InvalidOperation(f"number where a decimal string is required: {value!r}")
    return Decimal(str(value))


def _violation(row: FloorRow, detail: str) -> str:
    return f"{row.describe()} in FINAL.md {row.source}: {detail}"


# ---------------------------------------------------------------------------
# Individual row checks
# ---------------------------------------------------------------------------
def _check_settlement(policy: Mapping[str, Any]) -> list[str]:
    """Row 22: PAID -> FINAL must be at least 48 h and at least the rail's window.

    SWIFT is never FINAL by timer, so ``final_by_timer: false`` is *required*,
    not merely permitted, and it has no day window to check.
    """
    problems: list[str] = []
    settlement = policy.get("settlement")
    row = next(r for r in FLOOR_ROWS if r.number == 22)
    if not isinstance(settlement, Mapping):
        return [_violation(row, "settlement block is missing")]

    for rail, spec in settlement.items():
        if not isinstance(spec, Mapping):
            problems.append(_violation(row, f"{rail} is not a mapping"))
            continue

        if rail == "SWIFT":
            if spec.get("final_by_timer") is not False:
                problems.append(_violation(row, "SWIFT must set final_by_timer: false"))
            days = spec.get("presumed_settled_business_days")
            if not isinstance(days, int) or days < 10:
                problems.append(
                    _violation(
                        row, f"SWIFT.presumed_settled_business_days is {days!r}, floor is 10"
                    )
                )
            continue

        floor = SETTLE_FLOOR.get(rail)
        if floor is None:
            problems.append(_violation(row, f"unknown rail {rail!r}"))
            continue

        min_hours = spec.get("min_hours")
        if isinstance(min_hours, bool) or not isinstance(min_hours, int):
            problems.append(_violation(row, f"{rail}.min_hours is {min_hours!r}, not an integer"))
        elif min_hours < MIN_SETTLE_HOURS:
            problems.append(
                _violation(row, f"{rail}.min_hours is {min_hours}, floor is {MIN_SETTLE_HOURS}")
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


def _check_reserve_floor(policy: Mapping[str, Any]) -> list[str]:
    """Row 21: the floor must be set at all, and never below the shipped value."""
    row = next(r for r in FLOOR_ROWS if r.number == 21)
    floor = policy.get("reserve_floor")
    if not isinstance(floor, Mapping) or not floor:
        return [_violation(row, "reserve_floor is missing; the executor would refuse to start")]

    problems: list[str] = []
    for currency, value in floor.items():
        if not isinstance(value, str):
            problems.append(_violation(row, f"{currency} floor is not a decimal string"))
            continue
        try:
            actual = Decimal(value)
        except InvalidOperation:
            problems.append(_violation(row, f"{currency} floor {value!r} is not a number"))
            continue
        if actual < 0:
            problems.append(_violation(row, f"{currency} floor is negative"))
            continue
        shipped = row.floor_value if isinstance(row.floor_value, Mapping) else {}
        reference = shipped.get(currency)
        if reference is None:
            continue
        try:
            minimum = Decimal(reference)
        except InvalidOperation:  # pragma: no cover - floor table is static
            continue
        if actual < minimum:
            problems.append(
                _violation(row, f"{currency} floor {value} is below the floor {reference}")
            )
    return problems


def _check_t0_enabled(policy: Mapping[str, Any]) -> list[str]:
    """Row 10: T0 must be a real boolean, and off unless a signed policy says otherwise.

    The loader separately requires two signatures whenever it is on, so all this
    row does is refuse a non-boolean, which would coerce.
    """
    row = next(r for r in FLOOR_ROWS if r.number == 10)
    value = _get(policy, "t0.enabled")
    if not isinstance(value, bool):
        return [_violation(row, f"t0.enabled is {value!r}, not a boolean")]
    return []


def check_row(row: FloorRow, policy: Mapping[str, Any]) -> list[str]:
    """Return the violations for one row. An empty list means the row holds."""
    if row.number == 21:
        return _check_reserve_floor(policy)
    if row.number == 22:
        return _check_settlement(policy)
    if row.number == 10:
        return _check_t0_enabled(policy)

    if row.number == 9:
        actual = _get(policy, "t0.disqualifiers")
        if not isinstance(actual, list):
            return [_violation(row, f"t0.disqualifiers is {type(actual).__name__}, not a list")]
        missing = [flag for flag in row.floor_value if flag not in actual]
        if missing:
            return [_violation(row, f"t0.disqualifiers dropped {', '.join(missing)}")]
        return []

    if row.direction is Direction.SUPERSET:  # pragma: no cover - row 9 handled above
        return [_violation(row, "superset rows need a bespoke check")]

    actual = _get(policy, row.path or "")

    if row.number == 25:
        # The fee reservation is a floor: reducing it would let the planner
        # promise a reserve the wallet does not hold.
        try:
            if actual is None or _as_decimal(actual) < _as_decimal(row.floor_value):
                return [_violation(row, f"{row.path} is {actual!r}, floor is {row.floor_value}")]
        except InvalidOperation:
            return [_violation(row, f"{row.path} is not a decimal string")]
        return []

    if row.number == 29:
        # Never shorten a rail's flight time.
        if not isinstance(actual, int) or actual < int(row.floor_value):
            return [_violation(row, f"{row.path} is {actual!r}, minimum is {row.floor_value}")]
        return []

    if row.number in {6, 7, 8}:
        # T0 band rows. A tighter policy is allowed; looser is not.
        pass

    if isinstance(row.floor_value, str):
        try:
            actual_decimal = _as_decimal(actual)
            floor_decimal = Decimal(row.floor_value)
        except (InvalidOperation, TypeError):
            return [_violation(row, f"{row.path} is {actual!r}, not a decimal string")]
        if row.direction is Direction.MINIMUM and actual_decimal < floor_decimal:
            return [_violation(row, f"{row.path} is {actual}, floor is {row.floor_value}")]
        if row.direction is Direction.MAXIMUM and actual_decimal > floor_decimal:
            return [_violation(row, f"{row.path} is {actual}, ceiling is {row.floor_value}")]
        return []

    if isinstance(row.floor_value, int) and not isinstance(row.floor_value, bool):
        if not isinstance(actual, int) or isinstance(actual, bool):
            return [_violation(row, f"{row.path} is {actual!r}, not an integer")]
        if row.direction is Direction.MINIMUM and actual < row.floor_value:
            return [_violation(row, f"{row.path} is {actual}, floor is {row.floor_value}")]
        if row.direction is Direction.MAXIMUM and actual > row.floor_value:
            return [_violation(row, f"{row.path} is {actual}, ceiling is {row.floor_value}")]
        return []

    return []


def check_policy_against_floor(policy: Mapping[str, Any]) -> FloorResult:
    """Check every row. Returns all violations, not just the first.

    Reporting them together matters: an operator fixing a policy needs the whole
    list, and a test asserting one row at a time still gets a precise message.
    """
    violations: list[str] = []
    for row in FLOOR_ROWS:
        violations.extend(check_row(row, policy))
    return FloorResult(ok=not violations, violations=violations)


# ---------------------------------------------------------------------------
# Shape validation: unknown and missing keys
# ---------------------------------------------------------------------------
def _check_shape_at(value: Any, shape: Shape, path: str, problems: list[str]) -> None:
    """Recursively compare one value against its declared shape.

    Reports every unknown key and every type mismatch rather than stopping at
    the first, because an operator fixing a policy file needs the whole list.
    """
    if shape is FREEMAP:
        if not isinstance(value, Mapping):
            problems.append(f"{path} must be a mapping, got {type(value).__name__}")
            return
        for key, item in value.items():
            if not isinstance(key, str):
                problems.append(f"{path} has a non-string key {key!r}")
            elif shape_is_money_leaf(item) is False and isinstance(item, bool):
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
                problems.append(f"unknown key {path + '.' if path else ''}{key!r} (FINAL.md §4.15)")
        for key, child in shape.items():
            if key not in value:
                continue
            child_path = f"{path}.{key}" if path else key
            _check_shape_at(value[key], child, child_path, problems)
        return

    # Leaf.
    if shape == MONEY:
        if isinstance(value, bool):
            problems.append(f"{path} must be a decimal string, not a bool")
        elif isinstance(value, (int, float)):
            problems.append(
                f"{path} must be a decimal string, not a {type(value).__name__}: "
                "a float is not a signed amount (FINAL.md §7.3)"
            )
        elif not isinstance(value, str):
            problems.append(f"{path} must be a decimal string, got {type(value).__name__}")
        elif value.strip() != value or not value:
            problems.append(f"{path} is not a clean decimal string: {value!r}")
        else:
            try:
                Decimal(value)
            except InvalidOperation:
                problems.append(f"{path} is not a number: {value!r}")
        return

    if shape == NUM:
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"{path} must be an integer, got {value!r}")
        elif value < 0:
            problems.append(f"{path} must not be negative, got {value}")
        return

    if shape == BOOL:
        if not isinstance(value, bool):
            row = PATH_TO_ROW.get(path)
            suffix = f" (FINAL.md §4.15 r{row})" if row else ""
            problems.append(f"{path} must be a boolean, got {value!r}{suffix}")
        return

    if not isinstance(value, str):
        problems.append(f"{path} must be a string, got {type(value).__name__}")


#: Reverse index, so a structural error can name the floor row it offends.
#: Without this, "t0.enabled must be a boolean" is a confusing way to learn that
#: you have just attempted to loosen r10.
PATH_TO_ROW: dict[str, int] = {
    "t0.enabled": 10,
    "t0.disqualifiers": 9,
    "t0.per_payment_limit_usd": 6,
    "t0.min_final_payments": 7,
    "t0.max_multiple_of_payee_median": 8,
    "bank_change.cooling_off_hours": 1,
    "bank_change.callback_contact_min_age_days": 2,
    "bank_change.callback_validity_days": 3,
    "bank_change.first_payment_cap_usd": 4,
    "bank_change.cap_lift_final_payments": 5,
    "tiers.t2_threshold_usd": 11,
    "tiers.t2_payee_7d_aggregate_usd": 12,
    "reserve_floor": 21,
    "settlement": 22,
    "ambiguous.escalate_after_days": 23,
    "killswitch.clock_skew_seconds": 24,
    "killswitch.ambiguous_creates_per_run": 26,
    "killswitch.failed_transfers_rolling_1h": 27,
    "killswitch.extraction_conflicts_rolling_24h": 28,
    "killswitch.clear_signatures": 30,
    "approvals.max_validity_hours": 18,
    "fx.quote_safety_margin_seconds": 19,
    "fx.drift_bp": 20,
    "limits.per_run": 13,
    "limits.per_day": 14,
    "limits.per_payee_7d": 15,
    "limits.per_payee_24h": 16,
    "limits.per_approver_day_usd": 17,
}


def shape_is_money_leaf(value: Any) -> bool | None:
    """True when ``value`` can never be a valid money string.

    Used by the FREEMAP branch, where the leaf type is not declared per key:
    a boolean in a free mapping is always wrong, a number usually is.
    """
    return not isinstance(value, bool)


def _check_shape(policy: Mapping[str, Any]) -> list[str]:
    """Unknown keys and wrong types, walked recursively against :data:`SCHEMA`."""
    problems: list[str] = []
    for key in policy:
        if key not in SCHEMA:
            problems.append(
                f"unknown top-level key {key!r} (FINAL.md §4.15: an unknown key is a load error)"
            )
    for key, shape in SCHEMA.items():
        if key in policy:
            _check_shape_at(policy[key], shape, key, problems)
    return problems


def _check_roster(policy: Mapping[str, Any]) -> list[str]:
    """Unique emails, and a role of approver or ops only (§4.8, D6)."""
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
    """All structural problems, independent of any floor bound."""
    return [*_check_shape(policy), *_check_roster(policy)]
