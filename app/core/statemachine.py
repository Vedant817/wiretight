"""State machines as pure functions.

FINAL.md §8.3-§8.4. No I/O here. The poller and the executor call these; they
never write to the database themselves, which is what makes the rules testable
without a fake.

Two ideas do most of the work:

1. **First sight wins for failures.** ``failure_type`` is captured the first
   time it appears, whether that is the ``FAILED`` object or the auto-cancelled
   one, and is never nulled afterwards. Airwallex cancels a failed transfer
   within seconds, so a design that only reads ``FAILED`` loses the evidence.
2. **Documented transitions only, regressions ignored.** The sandbox occasionally
   reports a status we have already passed. Following it backwards would be
   wrong, so the previous state is kept and the regression is audited.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# §8.3 Airwallex transfer statuses and their documented transitions
# ---------------------------------------------------------------------------
AWX_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "IN_APPROVAL",
        "SCHEDULED",
        "OVERDUE",
        "PROCESSING",
        "SENT",
        "PAID",
        "FAILED",
        "CANCELLED",
    }
)

#: Only these edges exist in the documentation. Anything else is a regression or
#: a status we do not know.
DOCUMENTED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "IN_APPROVAL": frozenset({"PROCESSING", "CANCELLED"}),
    "SCHEDULED": frozenset({"PROCESSING", "OVERDUE", "CANCELLED"}),
    "OVERDUE": frozenset({"PROCESSING", "CANCELLED"}),
    "PROCESSING": frozenset({"SENT", "FAILED"}),
    "SENT": frozenset({"PAID", "FAILED"}),
    "PAID": frozenset({"FAILED"}),  # a bank return. PAID is not final.
    "FAILED": frozenset({"CANCELLED"}),  # automatic, within seconds
    "CANCELLED": frozenset(),
}

TERMINAL_AWX: Final[frozenset[str]] = frozenset({"CANCELLED"})


def is_terminal_awx(status: str | None) -> bool:
    """True when no further transition is expected.

    ``FAILED`` is *not* terminal in the polling sense: Airwallex cancels it
    automatically, and we need to keep reading to capture the reason.
    """
    return status in TERMINAL_AWX


def transfer_next_awx(current: str | None, observed: str) -> str:
    """Return the ``awx_status`` after observing ``observed``.

    * an unknown status keeps the previous state (and the caller opens an
      ``UNKNOWN_STATUS`` incident);
    * a documented regression keeps the previous state and is audited;
    * a terminal state never moves.
    """
    if observed not in AWX_STATUSES:
        return current or observed

    if current is None:
        return observed
    if current in TERMINAL_AWX:
        return current

    allowed = DOCUMENTED_TRANSITIONS.get(current, frozenset())
    if observed in allowed:
        return observed

    # Either a regression (SENT -> PROCESSING) or a jump we do not document.
    # Keep where we are; the audit trail records that we saw it.
    return current


def is_regression(current: str | None, observed: str) -> bool:
    """True when ``observed`` moves a known status backwards."""
    if current is None or observed not in AWX_STATUSES:
        return False
    if current in TERMINAL_AWX:
        return True
    return observed in AWX_STATUSES and observed not in DOCUMENTED_TRANSITIONS.get(
        current, frozenset()
    )


# ---------------------------------------------------------------------------
# §4.10 our overlay, which is never Airwallex's vocabulary
# ---------------------------------------------------------------------------
WT_STATES: Final[frozenset[str]] = frozenset(
    {
        "SUBMITTING",
        "AMBIGUOUS",
        "REJECTED",
        "PAID_PROVISIONAL",
        "FINAL",
        "PRESUMED_SETTLED",
        "REOPENED",
        "RFI_OPEN",
        "CANCELLED_FAILED",
    }
)


@dataclass(frozen=True)
class TransferObservation:
    """Result of folding one polled observation into the current state."""

    awx_status: str | None
    failure_type: str | None
    failure_reason: str | None
    regression: bool = False
    unknown_status_incident: bool = False
    late_failure_after_final: bool = False


def apply_transfer_observation(
    *,
    awx_status: str,
    failure_type: str | None,
    failure_reason: str | None,
    current_awx_status: str | None = None,
    current_failure_type: str | None = None,
    current_failure_reason: str | None = None,
    wt_state: str | None = None,
) -> TransferObservation:
    """Fold one observation in. The heart of §4.11's "first sight" rule.

    ``failure_type`` and ``failure_reason`` are captured the first time they are
    seen and never overwritten. A later observation without them, or with
    different ones, leaves the originals intact: the evidence of what actually
    went wrong is not something a subsequent poll gets to edit.
    """
    unknown = awx_status not in AWX_STATUSES
    regression = is_regression(current_awx_status, awx_status)
    next_awx = transfer_next_awx(current_awx_status, awx_status)

    # First sight wins. Either the FAILED object or the auto-cancelled one.
    # A later observation never overwrites what we already recorded.
    kept_type: str | None = (
        current_failure_type if current_failure_type is not None else failure_type
    )
    kept_reason: str | None = (
        current_failure_reason if current_failure_type is not None else failure_reason
    )

    # A FAILED seen after we already declared FINAL is never ignored (§4.10).
    late_failure = bool(wt_state == "FINAL" and awx_status == "FAILED")

    return TransferObservation(
        awx_status=next_awx,
        failure_type=kept_type,
        failure_reason=kept_reason,
        regression=regression,
        unknown_status_incident=unknown,
        late_failure_after_final=late_failure,
    )


# ---------------------------------------------------------------------------
# §8.4 payee version machine
# ---------------------------------------------------------------------------
PAYEE_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "PROPOSED",
        "ACTIVE_CAPPED",
        "ACTIVE",
        "SUSPENDED",
        "SUPERSEDED",
        "REJECTED",
        "RETIRED",
        "COMPLIANCE_HOLD",
    }
)

#: Floor row 5: the first-payment cap lifts after this many FINAL payments.
CAP_LIFT_FINAL_PAYMENTS: Final[int] = 2

_TERMINAL_PAYEE: Final[frozenset[str]] = frozenset({"REJECTED", "RETIRED", "SUPERSEDED"})


def payee_next(current: str, event: str) -> str:
    """Fold a payee event into the payee version status.

    Events: ``APPROVED`` · ``FINAL:<n>`` · ``FAILURE`` · ``COMPLIANCE`` ·
    ``SUPERSEDED``.

    Compliance takes precedence over everything: a payee under
    ``COMPLIANCE_HOLD`` never advances, no matter how many payments settle.
    """
    if current in _TERMINAL_PAYEE:
        return current
    if current == "COMPLIANCE_HOLD":
        return current

    if event == "COMPLIANCE":
        return "COMPLIANCE_HOLD"
    if event == "FAILURE":
        return "SUSPENDED"
    if event == "SUPERSEDED":
        return "SUPERSEDED"

    if current == "PROPOSED" and event == "APPROVED":
        return "ACTIVE_CAPPED"

    if event.startswith("FINAL:"):
        try:
            count = int(event.split(":", 1)[1])
        except (IndexError, ValueError):
            return current
        if current == "ACTIVE_CAPPED" and count >= CAP_LIFT_FINAL_PAYMENTS:
            return "ACTIVE"
        if current == "ACTIVE_CAPPED":
            return "ACTIVE_CAPPED"

    return current


# ---------------------------------------------------------------------------
# §8.4 change request machine
# ---------------------------------------------------------------------------
CHANGE_REQUEST_STATUSES: Final[frozenset[str]] = frozenset(
    {"RECEIVED", "PENDING_CALLBACK", "COOLING_OFF", "APPROVED", "REJECTED", "EXPIRED", "WITHDRAWN"}
)

_TERMINAL_CHANGE: Final[frozenset[str]] = frozenset({"REJECTED", "EXPIRED", "WITHDRAWN"})

#: Floor row 3: a callback is valid for this many days after the request.
CALLBACK_VALIDITY_DAYS: Final[int] = 7


def change_request_next(current: str, event: str) -> str:
    """Fold a change-request event into its status.

    ``REJECTED`` and ``EXPIRED`` are terminal and never reopened (§4.5.1):
    releasing a wrongly rejected supplier means a **new** request through the
    same callback rules, not reopening this one.
    """
    if current in _TERMINAL_CHANGE:
        return current

    if event == "REQUEST_CALLBACK" and current in {"RECEIVED", "PENDING_CALLBACK"}:
        return "PENDING_CALLBACK"
    if event == "CALLBACK:CONFIRMED" and current == "PENDING_CALLBACK":
        return "COOLING_OFF"
    if event == "COOLING_OFF_ENDED" and current == "COOLING_OFF":
        return "APPROVED"
    if event in {"CALLBACK:DENIED", "NO_CHANGE_MADE"} and current == "PENDING_CALLBACK":
        return "REJECTED"
    if event == "EXPIRED":
        return "EXPIRED"
    if event == "WITHDRAWN":
        return "WITHDRAWN"
    return current


# ---------------------------------------------------------------------------
# §8.4 conversions and RFIs
# ---------------------------------------------------------------------------
CONVERSION_STATUSES: Final[frozenset[str]] = frozenset(
    {"CREATED", "SETTLED", "SCHEDULED", "OVERDUE", "CANCELLED"}
)

_TERMINAL_CONVERSION: Final[frozenset[str]] = frozenset({"SETTLED", "CANCELLED"})


def conversion_next(current: str, observed: str) -> str:
    """A conversion is only usable once ``SETTLED``; a PAYMENT packet waits."""
    if current in _TERMINAL_CONVERSION:
        return current
    if observed in _TERMINAL_CONVERSION:
        return observed
    return current


RFI_STATUSES: Final[frozenset[str]] = frozenset({"ACTION_REQUIRED", "ANSWERED", "CLOSED"})


def rfi_next(current: str, observed: str) -> str:
    if current == "CLOSED":
        return current
    return observed if observed in RFI_STATUSES else current


# ---------------------------------------------------------------------------
# §8.2 obligation states
# ---------------------------------------------------------------------------
OBLIGATION_CLOSED_PREFIXES: Final[tuple[str, ...]] = ("CLOSED",)


def is_hard_blocked(state: str) -> bool:
    """HARD_BLOCK and the quarantine/compliance states move no money (§4.4)."""
    return (
        state.startswith("HOLD:")
        or state.startswith("QUARANTINE:")
        or state == "COMPLIANCE_HOLD"
        or state == "FAILED_REJECTED"
    )
