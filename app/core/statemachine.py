"""State machines as pure functions.

FINAL.md §8.3-§8.4. No I/O here. The poller and the executor call these; they
never write to the database themselves, which is what makes the rules testable
without provider I/O.

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


def _reachable(current: str, observed: str) -> bool:
    pending = list(DOCUMENTED_TRANSITIONS.get(current, ()))
    visited: set[str] = set()
    while pending:
        value = pending.pop()
        if value == observed:
            return True
        if value not in visited:
            visited.add(value)
            pending.extend(DOCUMENTED_TRANSITIONS.get(value, ()))
    return False


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

    if _reachable(current, observed):
        return observed

    # Either a regression (SENT -> PROCESSING) or a jump we do not document.
    # Keep where we are; the audit trail records that we saw it.
    return current


def is_regression(current: str | None, observed: str) -> bool:
    """True when ``observed`` moves a known status backwards.

    Re-observing the same status, or observing a terminal one we already hold,
    is not a regression. The poller reads the same object repeatedly, and
    flagging every one of those as an anomaly would bury a real one in noise.
    """
    if current is None or observed not in AWX_STATUSES:
        return False
    if observed == current:
        return False
    if current in TERMINAL_AWX:
        return True
    return not _reachable(current, observed)


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


def _present(value: str | None) -> str | None:
    """Normalise an observed failure field, keeping ``None`` for "not present".

    Airwallex can return ``""`` or a whitespace-only string where a field is
    absent. Those are stored as ``NULL``, not as an empty string.

    The distinction matters, and it was found by a property test rather than by
    reading. ``failure_type`` must be in exactly one of two states - absent, or a
    real type - because "never nulled" (§4.11) and the failure playbook (§4.12) both
    read from it. A third state, an empty string, is neither: it is truthy to a
    ``is not None`` check, so a code path reading the column concludes a failure
    *was* recorded while ``playbook_for("")`` reports an unknown type. And an
    incident rerun would keep the blank, so the real value arriving later would
    be ignored as "already captured".

    Stripping rather than rejecting keeps the capture direction simple: a blank
    is absent evidence, which is the same as no evidence.
    """
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


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

    ``failure_type`` and ``failure_reason`` are captured independently, the first
    time each is seen, and neither is ever overwritten afterwards.

    The two are independent on purpose. §4.11's group H covers the case where a
    bare cancel returns only ``failure_reason: "simulation"`` and no
    ``failure_type``: gating the reason's first-sight on whether a *type* was
    already recorded let a stored reason be replaced whenever a later poll
    supplied a type and the type column happened to be empty.
    """
    unknown = awx_status not in AWX_STATUSES
    regression = is_regression(current_awx_status, awx_status)
    next_awx = transfer_next_awx(current_awx_status, awx_status)

    # Absent, not blank. See _present: an empty string would be a third state
    # between "no failure recorded" and "this failure was recorded".
    incoming_type = _present(failure_type)
    incoming_reason = _present(failure_reason)

    kept_type: str | None = (
        current_failure_type if current_failure_type is not None else incoming_type
    )
    kept_reason: str | None = (
        current_failure_reason if current_failure_reason is not None else incoming_reason
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
# The wt_state overlay (§4.10)
# ---------------------------------------------------------------------------
#: §4.10: "PAID is provisional; FINAL is our label after the rail's business-day
#: return window." The overlay is never Airwallex's vocabulary, and PAID never
#: becomes FINAL on its own — it needs the return window to elapse.
WT_TERMINAL: Final[frozenset[str]] = frozenset(
    {"FINAL", "PRESUMED_SETTLED", "CANCELLED_FAILED", "REJECTED"}
)


def is_terminal_wt(state: str | None) -> bool:
    return state in WT_TERMINAL


def wt_next(
    current: str | None,
    *,
    awx_status: str | None,
    ambiguous: bool = False,
    rfi_open: bool = False,
    final_due: bool = False,
    presumed_settled: bool = False,
) -> str:
    """Advance our overlay from the sandbox's status.

    Precedence, highest first, because these are not independent:

    1. ``REJECTED`` — a definitive validation refusal. The create never landed.
    2. ``CANCELLED_FAILED`` — the auto-cancel after a failure.
    3. ``RFI_OPEN`` — Airwallex wants information; holds new payments.
    4. ``AMBIGUOUS`` — we do not know whether the create landed. §4.8 step 8:
       resolved only by lookup with the same key.
    5. ``REOPENED`` — a FAILED after FINAL. Never ignored (§4.10).
    6. ``FINAL`` / ``PRESUMED_SETTLED`` — only when the window has actually
       elapsed. SWIFT never reaches FINAL by timer.
    7. ``PAID_PROVISIONAL`` — PAID, still inside the return window.
    8. ``SUBMITTING`` — anything else in flight.

    A late failure outranks FINAL because that is the whole point of treating
    PAID as provisional.
    """
    if current in WT_TERMINAL and not (current == "FINAL" and awx_status == "FAILED"):
        return current

    if awx_status == "CANCELLED":
        return "CANCELLED_FAILED"
    if rfi_open:
        return "RFI_OPEN"
    if ambiguous:
        return "AMBIGUOUS"
    if current == "FINAL" and awx_status == "FAILED":
        return "REOPENED"
    if final_due:
        return "FINAL"
    if presumed_settled:
        return "PRESUMED_SETTLED"
    if awx_status == "PAID":
        return "PAID_PROVISIONAL"
    if awx_status in {
        "FAILED",
        "CANCELLED",
        "SCHEDULED",
        "OVERDUE",
        "PROCESSING",
        "SENT",
        "IN_APPROVAL",
    }:
        return current or "SUBMITTING"
    return current or "SUBMITTING"


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


#: Every event §4.5.1 defines, plus the reason discriminator. Anything else is a
#: spelling mistake at a call site, and returning the current state for it silently
#: would leave a change request stuck in ``PENDING_CALLBACK`` forever with nothing
#: logged - which is the point of naming it (D-B22, gap 7).
CHANGE_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "REQUEST_CALLBACK",
        "CALLBACK:CONFIRMED",
        "CALLBACK:DENIED",
        "NO_CHANGE_MADE",
        "COOLING_OFF_ENDED",
        "EXPIRED",
        "WITHDRAWN",
    }
)


class UnknownEventError(ValueError):
    """An event this machine does not know.

    Raised rather than returned-as-no-op. Returning the current state is right for
    an event that does not apply *yet* - that is normal in a state machine - but not
    for something that is not an event at all. "Not yet" and "never" need different
    responses, and the difference cannot be recovered afterwards.
    """


def change_request_next(current: str, event: str) -> str:
    """Fold a change-request event into its status.

    ``REJECTED`` and ``EXPIRED`` are terminal and never reopened (§4.5.1):
    releasing a wrongly rejected supplier means a **new** request through the
    same callback rules, not reopening this one.

    An **unknown** event raises. Returning the current state for one - which is
    what this did before - is a silent no-op, and a typo at a call site
    (``CALLBACK:CONFIRMED`` written as ``callback:confirmed``) would strand the
    request in ``PENDING_CALLBACK`` forever with no error anywhere.
    """
    if event not in CHANGE_EVENTS:
        raise UnknownEventError(
            f"unknown change-request event {event!r}. Known events are "
            f"{sorted(CHANGE_EVENTS)}. Returning the current state for an unknown "
            "event would strand the request silently (FINAL.md §4.5.1)."
        )

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
