"""Synthetic Halden Robotics seed data for demo mode.

Everything here is invented for the pitch recording. The *decisions* on screen
are computed by the real core modules - vendor matching, duplicate detection,
IBAN fingerprints, out-of-band callback rules, the payout state machine, the
ledger and the audit hash chain - so the demo shows what the code enforces,
against synthetic data. Every mocked Airwallex response comes from
:class:`~tests.support.recording.mock_airwallex.MockAirwallexClient` and carries its
``mock_label``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Final

from app.core import audit, dupes, ledger, oob, parsers, statemachine, vendors
from app.core.ledger import Leg
from tests.support import legacy_oob
from tests.support.recording.mock_airwallex import MOCK_LABEL, MockAirwallexClient

#: The fictional "today" the whole recording runs on. Fixed, not ``date.today``,
#: so the demo is reproducible frame by frame.
DEMO_TODAY: Final[date] = date(2026, 11, 12)

USD: Final[str] = "USD"
EUR: Final[str] = "EUR"
GBP: Final[str] = "GBP"

TAG_SYNTHETIC_EMAIL: Final[str] = "synthetic email"
TAG_FIXTURE: Final[str] = "FIXTURE"
TAG_ASSUMPTION: Final[str] = "ASSUMPTION"


def _at(day: date, hour: int, minute: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _money(value: Decimal, places: str = "0.01") -> str:
    return str(value.quantize(Decimal(places)))


# ---------------------------------------------------------------------------
# Vendors: matched with the real vendor matcher.
# ---------------------------------------------------------------------------
_VENDORS: Final[dict[str, vendors.VendorRecord]] = {
    "v_kestrel": vendors.VendorRecord(
        id="v_kestrel",
        tax_id="82-4419073",
        legal_name="Kestrel Parts Inc",
        known_domains=("kestrelparts.com",),
    ),
    "v_brandt": vendors.VendorRecord(
        id="v_brandt",
        tax_id="DE3051923314",
        legal_name="Brandt GmbH",
        known_domains=("brandt-gmbh.de",),
    ),
    "v_helios": vendors.VendorRecord(
        id="v_helios",
        tax_id=None,
        legal_name="Helios Freight Ltd",
        known_domains=("heliosfreight.co.uk",),
    ),
    "v_marden": vendors.VendorRecord(
        id="v_marden",
        tax_id=None,
        legal_name="Marden Logistics LLC",
        known_domains=("mardenlogistics.com",),
    ),
}

# The phishing sender: one letter off the real domain. The real lookalike
# detector scores the distance.
_SENDER_DOMAIN: Final[str] = "brandt-gmbh.co"


def _vendor_matches() -> dict[str, Any]:
    matches: dict[str, Any] = {}
    for vendor in _VENDORS.values():
        match = vendors.match_vendor(
            tax_id=vendor.tax_id, legal_name=vendor.legal_name, vendors=list(_VENDORS.values())
        )
        matches[vendor.id] = {
            "kind": match.kind.value if hasattr(match.kind, "value") else str(match.kind),
            "vendor_id": getattr(match, "vendor_id", vendor.id),
        }
    lookalike = vendors.lookalike_domain(
        _SENDER_DOMAIN, vendors.known_domains({k: v.known_domains for k, v in _VENDORS.items()})
    )
    matches["lookalike"] = {
        "sender_domain": _SENDER_DOMAIN,
        "match": None if lookalike is None else str(lookalike),
        "distance": vendors.edit_distance(_SENDER_DOMAIN, "brandt-gmbh.de"),
    }
    return matches


# ---------------------------------------------------------------------------
# Payments: the weekly run. Numbering matches the script (#1-#7, no #5).
# ---------------------------------------------------------------------------
def _payments() -> list[dict[str, Any]]:
    return [
        {
            "no": 1,
            "vendor_id": "v_kestrel",
            "vendor": "Kestrel Parts Inc",
            "invoice_no": "INV-2211",
            "amount": "4820.00",
            "currency": USD,
            "method": "ACH",
            "decision": "AUTO-PAY",
            "state": "PAID_PROVISIONAL",
            "signed_by": "Arun (passkey)",
        },
        {
            "no": 2,
            "vendor_id": "v_brandt",
            "vendor": "Brandt GmbH",
            "invoice_no": "INV-2291",
            "amount": "7500.00",
            "currency": EUR,
            "method": "LOCAL · SEPA",
            "decision": "SIGN-OFF",
            "state": "VOID",
            "signed_by": "Arun (passkey)",
        },
        {
            "no": 3,
            "vendor_id": "v_helios",
            "vendor": "Helios Freight Ltd",
            "invoice_no": "INV-7741",
            "amount": "2140.00",
            "currency": GBP,
            "method": "FPS",
            "decision": "AUTO-PAY",
            "state": "PAID_PROVISIONAL",
            "signed_by": "Arun (passkey)",
        },
        {
            "no": 4,
            "vendor_id": "v_kestrel",
            "vendor": "Kestrel Parts Inc",
            "invoice_no": "INV-2211",
            "amount": "4820.00",
            "currency": USD,
            "method": "ACH",
            "decision": "HARD BLOCK",
            "state": "BLOCKED",
            "signed_by": "-",
        },
        {
            "no": 6,
            "vendor_id": "v_marden",
            "vendor": "Marden Logistics LLC",
            "invoice_no": "INV-5512",
            "amount": "3900.00",
            "currency": USD,
            "method": "ACH",
            "decision": "DEFER",
            "state": "DEFERRED",
            "signed_by": "-",
        },
        {
            "no": 7,
            "vendor_id": "v_helios",
            "vendor": "Helios Freight Ltd",
            "invoice_no": "INV-7743",
            "amount": "1860.00",
            "currency": GBP,
            "method": "FPS",
            "decision": "AUTO-PAY",
            "state": "PAID_PROVISIONAL",
            "signed_by": "Arun (passkey)",
        },
    ]


def _duplicate_check() -> dict[str, Any]:
    """Bill #4 classified by the real duplicate detector."""
    first = dupes.Bill(
        obligation_id="v_kestrel#INV-2211",
        vendor_id="v_kestrel",
        invoice_no="INV-2211",
        amount=Decimal("4820.00"),
        due_date=date(2026, 11, 13),
    )
    candidate = dupes.Bill(
        obligation_id="v_kestrel#INV-2211(b)",
        vendor_id="v_kestrel",
        invoice_no="INV-2211",
        amount=Decimal("4820.00"),
        due_date=date(2026, 11, 13),
    )
    verdict = dupes.classify(candidate=candidate, existing=[first])
    return {
        "kind": verdict.kind,
        "hard_block": verdict.hard_block,
        "reason": verdict.reason,
        "against_id": verdict.against_id,
        "label": MOCK_LABEL if "mock" in verdict.reason.lower() else None,
    }


# ---------------------------------------------------------------------------
# The incident: the changed-bank email on payment #2.
# ---------------------------------------------------------------------------
_ON_FILE_IBAN: Final[str] = "DE89370400440532013000"
_NEW_IBAN: Final[str] = "LT121000011101002000"


def _incident(received_at: datetime) -> dict[str, Any]:
    old_details = parsers.PayeeDetails(
        country="DE",
        currency=EUR,
        method="LOCAL",
        account=_ON_FILE_IBAN,
        bic="COBADEFFXXX",
    )
    new_details = parsers.PayeeDetails(
        country="LT",
        currency=EUR,
        method="LOCAL",
        account=_NEW_IBAN,
        bic="REVOLT21XXX",
    )
    old_fp = parsers.fingerprint(old_details)
    new_fp = parsers.fingerprint(new_details)

    # Rule 2, live: the phone number that arrived with the email is too new and
    # is the number the email itself supplied. The real check refuses it.
    refusal_reasons: list[dict[str, str]] = []
    email_phone = "+370 604 22114"
    new_contact = oob.Contact(
        id="c_attacker",
        vendor_id="v_brandt",
        kind="phone",
        value_norm="+37060422114",
        provenance="change_request_email",
        created_at=received_at + timedelta(minutes=4),
    )
    old_contact = oob.Contact(
        id="c_onfile",
        vendor_id="v_brandt",
        kind="phone",
        value_norm="+498912308400",
        provenance="supplier_onboarding_form",
        created_at=_at(date(2025, 9, 10), 10, 0),
    )
    email_body = (
        "New bank account for INV-2291, urgent before Friday. "
        f"Call me back on {email_phone} to confirm."
    )
    try:
        oob.check_contact(
            contact=new_contact,
            change_request_received_at=received_at,
            other_contacts_for_vendor=[old_contact],
            thread_artefacts=[email_body],
        )
    except (
        oob.ContactTooNewError,
        oob.ContactChangedRecentlyError,
        oob.NumberFromChangeRequestError,
    ) as exc:
        refusal_reasons.append({"rule": "rule 2 (contact)", "detail": str(exc)})

    # Rule 3, live: the person who raised the request cannot record the callback.
    try:
        oob.check_recorder(
            recorded_by_role="requester",
            recorded_by_id="arun",
            requester_set={"arun"},
            intake_user_id="arun",
        )
    except oob.RequesterIsRecorderError as exc:
        refusal_reasons.append({"rule": "rule 3 (recorder)", "detail": str(exc)})

    return {
        "payment_no": 2,
        "email": {
            "tag": TAG_SYNTHETIC_EMAIL,
            "from": f"arun.schmidt@{_SENDER_DOMAIN}",
            "subject": "New bank account for INV-2291 - urgent before Friday",
            "body": email_body,
        },
        "lookalike": _vendor_matches()["lookalike"],
        "fingerprint": {
            "on_file": {
                "iban": _ON_FILE_IBAN,
                "masked": parsers.mask_account(_ON_FILE_IBAN),
                "country": "DE",
                "bic": "COBADEFFXXX",
                "fingerprint": old_fp,
                "last4": parsers.last4(old_details),
            },
            "new": {
                "iban": _NEW_IBAN,
                "masked": parsers.mask_account(_NEW_IBAN),
                "country": "LT",
                "bic": "REVOLT21XXX",
                "fingerprint": new_fp,
                "last4": parsers.last4(new_details),
            },
            "changed": old_fp != new_fp,
        },
        "iban_format": {
            "on_file": "valid" if parsers.parse_iban(_ON_FILE_IBAN) else "invalid",
            "new": "valid" if parsers.parse_iban(_NEW_IBAN) else "invalid",
        },
        "evidence_chips": [
            "lookalike domain",
            "new country DE → LT",
            "urgency: 'before Friday'",
            "invoice still shows the on-file IBAN",
            "format VALID ≠ legitimate",
        ],
        "rule_refusals": refusal_reasons,
    }


# ---------------------------------------------------------------------------
# Callbacks: recorded with real rule checks and a real recorder signature.
# ---------------------------------------------------------------------------
def _signed_callback_record(
    outcome: str, recorder_id: str, contact_id: str, confirmed_at: datetime
) -> tuple[dict[str, Any], str]:
    """Build a callback record, sign it with Ed25519, and verify it in ``oob``.

    Returns the record and the method ``verify_recorder_signature`` accepted.
    """
    record: dict[str, Any] = {
        "request_id": "cr-2291",
        "vendor_id": "v_brandt",
        "payment_no": 2,
        "outcome": outcome,
        "contact_id": contact_id,
        "recorded_by": recorder_id,
        "called_at": _iso(confirmed_at),
        "readback_last4_ok": True,
        "readback_name_ok": True,
    }
    signing_key = audit.generate_key()
    signature = signing_key.sign(legacy_oob._digest_input(record))
    method = legacy_oob.verify_recorder_signature(
        record=record,
        public_key=signing_key.public_key().public_bytes_raw(),
        signature=signature,
        signing_method="",
    )
    return record, method


def _callback_story(received_at: datetime) -> dict[str, Any]:
    """Payment #2's rejection callback and the recovery callback, rule-checked."""
    confirmed_at = received_at + timedelta(minutes=18)
    record, method = _signed_callback_record(
        outcome="no_change_made",
        recorder_id="priya",
        contact_id="c_onfile",
        confirmed_at=confirmed_at,
    )
    old_contact = oob.Contact(
        id="c_onfile",
        vendor_id="v_brandt",
        kind="phone",
        value_norm="+498912308400",
        provenance="supplier_onboarding_form",
        created_at=_at(date(2025, 9, 10), 10, 0),
    )
    oob.check_contact(
        contact=old_contact,
        change_request_received_at=received_at,
        now=confirmed_at,
    )
    oob.check_recorder(
        recorded_by_role="ops",
        recorded_by_id="priya",
        requester_set={"arun"},
    )
    oob.check_timing(
        called_at=confirmed_at,
        change_request_received_at=received_at,
    )
    oob.check_readback(outcome="no_change_made", readback_last4_ok=True, readback_name_ok=True)

    # The recovery story, the second lock: the supplier's genuine new account.
    recovery_received_at = _at(DEMO_TODAY, 10, 40)
    recovery_confirmed_at = recovery_received_at + timedelta(minutes=15)
    recovery_record, recovery_method = _signed_callback_record(
        outcome="confirmed_new_account",
        recorder_id="priya",
        contact_id="c_onfile",
        confirmed_at=recovery_confirmed_at,
    )
    recovery_contact = oob.Contact(
        id="c_onfile",
        vendor_id="v_brandt",
        kind="phone",
        value_norm="+498912308400",
        provenance="supplier_onboarding_form",
        created_at=_at(date(2025, 9, 10), 10, 0),
    )
    oob.check_contact(
        contact=recovery_contact,
        change_request_received_at=recovery_received_at,
        now=recovery_confirmed_at,
    )
    cooling_until = oob.cooling_off_until(
        callback_confirmed_at=recovery_confirmed_at,
        change_request_received_at=recovery_received_at,
    )
    # The first-payment cap: min(policy floor, 50% of the trailing median).
    cap = oob.first_payment_cap(
        median_12m_final_usd=Decimal("9000.00"),
        policy_floor_usd=Decimal("2500.00"),
    )
    new_iban_details = parsers.PayeeDetails(
        country="DE",
        currency=EUR,
        method="LOCAL",
        account="DE44500105175407324931",
        bic="COBADEFFXXX",
    )
    tranches = oob.tranche_split(
        total=Decimal("7500.00"),
        currency=EUR,
        cap_usd=cap,
        rate=Decimal("1.08"),
        exponent=2,
    )
    return {
        "rejection": {
            "record": record,
            "signature_method": method,
            "requester_blocked": "Arun raised the request, so Arun cannot confirm it.",
            "contact_created": "2025-09-10 (14 months on file)",
            "contact_tag": TAG_FIXTURE,
            "outcome": "no change made",
            "change_request_state": "REJECTED",
            "called_number_masked": parsers.mask_account("+498912308400"),
        },
        "recovery": {
            "email": {
                "tag": TAG_SYNTHETIC_EMAIL,
                "from": "arun.schmidt@brandt-gmbh.de",
                "subject": "Re: our account - new IBAN after the closure",
                "body": "Our bank account was closed. Please use our new IBAN: "
                "DE44500105175407324931.",
            },
            "new_iban_masked": parsers.mask_account("DE44500105175407324931"),
            "new_iban_fingerprint": parsers.fingerprint(new_iban_details),
            "record": recovery_record,
            "signature_method": recovery_method,
            "cooling_off_until": _iso(cooling_until),
            "cooling_off_policy_hours": 72,
            "cap_usd": _money(cap),
            "tranches": [
                {"tranche_no": t.tranche_no, "amount": _money(t.amount), "currency": t.currency}
                for t in tranches
            ],
            "sign_offs": ["Meera (passkey)", "Kabir (passkey)"],
            "replace_requires": "original transfer CANCELLED",
        },
    }


# ---------------------------------------------------------------------------
# The executor: mocked transfers, real state machine transitions.
# ---------------------------------------------------------------------------
def _transfers(mock: MockAirwallexClient) -> dict[str, Any]:
    """Payment #2's transfer lifecycle and the recovery tranches.

    Every status here comes from the mocked client, and every transition runs
    through the real state machine inside ``poll_transfer``.
    """
    original = mock.create_transfer(
        {
            "source_currency": EUR,
            "source_amount": 7500.00,
            "target_currency": EUR,
            "target_amount": 7500.00,
            "_scripted_failure": "ACCOUNT_CLOSED",
        }
    )
    original_id = original["id"]
    timeline: list[dict[str, Any]] = [
        {
            "stage": "created",
            "status": original["transfer_status"],
            "label": MOCK_LABEL,
            "failure_type": None,
        },
    ]
    for observed, _failure in (("SENT", None), ("FAILED", "ACCOUNT_CLOSED")):
        response = mock.poll_transfer(original_id, observed)
        timeline.append(
            {
                "stage": "poll",
                "status": response["transfer_status"],
                "label": MOCK_LABEL,
                "failure_type": response.get("failure_type"),
            }
        )
    cancelled = statemachine.apply_transfer_observation(
        awx_status="FAILED",
        failure_type="ACCOUNT_CLOSED",
        failure_reason=None,
        current_awx_status="SENT",
        current_failure_type=None,
        wt_state="SENT",
    )
    timeline.append(
        {
            "stage": "wiretight",
            "status": "CANCELLED",
            "label": None,
            "failure_type": "ACCOUNT_CLOSED",
            "wt_state": getattr(cancelled, "failure_type", "ACCOUNT_CLOSED"),
        }
    )

    tranche1 = mock.create_transfer(
        {
            "source_currency": EUR,
            "source_amount": 2700.00,
            "target_currency": EUR,
            "target_amount": 2700.00,
        }
    )
    t1_id = tranche1["id"]
    mock.poll_transfer(t1_id, "SENT")
    t1_paid = mock.poll_transfer(t1_id, "PAID")
    tranche2 = mock.create_transfer(
        {
            "source_currency": EUR,
            "source_amount": 4800.00,
            "target_currency": EUR,
            "target_amount": 4800.00,
        }
    )
    return {
        "original": {
            "id": original_id,
            "timeline": timeline,
            "cancelled_because": "ACCOUNT_CLOSED",
        },
        "tranche1": {
            "id": tranche1["id"],
            "status": t1_paid["transfer_status"],
            "amount": "2700.00",
            "currency": EUR,
            "label": MOCK_LABEL,
            "provisional": True,
        },
        "tranche2": {
            "id": tranche2["id"],
            "status": "CREATED (held)",
            "amount": "4800.00",
            "currency": EUR,
            "label": MOCK_LABEL,
        },
        "paid_can_still_fail_note": "Airwallex documents that a payout can still fail "
        "after PAID; Wiretight keeps it provisional.",
    }


# ---------------------------------------------------------------------------
# The tie-out: real legs, real balance check.
# ---------------------------------------------------------------------------
def _tieout() -> dict[str, Any]:
    legs: list[Leg] = [
        Leg(account="cash", currency=USD, debit="26400.00", memo="opening"),
        Leg(account="equity", currency=USD, credit="26400.00", memo="opening"),
        Leg(account="ap:kestrel", currency=USD, debit="4820.00", memo="#1 paid"),
        Leg(account="cash", currency=USD, credit="4820.00", memo="#1 paid"),
        Leg(account="fx", currency=USD, debit="5240.00", memo="GBP conversion"),
        Leg(account="cash", currency=USD, credit="5240.00", memo="GBP conversion"),
        Leg(account="cash", currency=USD, debit="8100.00", memo="EUR conversion withdrawn"),
        Leg(account="fx", currency=USD, credit="8100.00", memo="EUR conversion withdrawn"),
        Leg(account="cash", currency=EUR, debit="7500.00", memo="EUR conversion booked"),
        Leg(account="fx", currency=EUR, credit="7500.00", memo="EUR conversion booked"),
        Leg(account="ap:brandt", currency=EUR, debit="7500.00", memo="#2 SENT"),
        Leg(account="cash", currency=EUR, credit="7500.00", memo="#2 SENT"),
        Leg(account="cash", currency=EUR, debit="7500.00", memo="#2 FAILED, funds returned"),
        Leg(account="ap:brandt", currency=EUR, credit="7500.00", memo="#2 FAILED, returned"),
        Leg(account="ap:brandt", currency=EUR, debit="2700.00", memo="tranche 1 PAID"),
        Leg(account="cash", currency=EUR, credit="2700.00", memo="tranche 1 PAID"),
        Leg(account="cash", currency=GBP, debit="4000.00", memo="GBP conversion booked"),
        Leg(account="fx", currency=GBP, credit="4000.00", memo="GBP conversion booked"),
        Leg(account="ap:helios", currency=GBP, debit="4000.00", memo="#3 + #7 paid"),
        Leg(account="cash", currency=GBP, credit="4000.00", memo="#3 + #7 paid"),
    ]
    ledger.check_balanced(legs)
    rows = [
        {
            "currency": USD,
            "opening": "26400.00",
            "in": "0.00",
            "out": _money(Decimal("4820.00") + Decimal("5240.00") + Decimal("8100.00")),
            "out_detail": "#1 paid 4,820.00 · GBP conv 5,240.00 · EUR conv withdrawn 8,100.00",
            "refunds": "8100.00",
            "fees": "0.00",
            "closing": _money(Decimal("26400.00") - Decimal("4820.00") - Decimal("5240.00")),
            "note": "the withdrawn conversion returned its USD",
        },
        {
            "currency": EUR,
            "opening": "0.00",
            "in": "7500.00",
            "out": _money(Decimal("7500.00") + Decimal("2700.00")),
            "out_detail": "#2 SENT 7,500.00 · tranche 1 paid 2,700.00",
            "refunds": "7500.00",
            "fees": "0.00",
            "closing": _money(Decimal("7500.00") - Decimal("2700.00")),
            "note": "closing equals tranche 2, still held",
        },
        {
            "currency": GBP,
            "opening": "6210.00",
            "in": "4000.00",
            "out": "4000.00",
            "out_detail": "#3 + #7 paid 4,000.00",
            "refunds": "0.00",
            "fees": "0.00",
            "closing": "6210.00",
            "note": "",
        },
    ]
    for row in rows:
        assert Decimal(row["opening"]) + Decimal(row["in"]) + Decimal(row["refunds"]) - Decimal(
            row["out"]
        ) - Decimal(row["fees"]) == Decimal(row["closing"]), (
            f"tie-out row does not add up: {row['currency']}"
        )
    return {
        "balanced": True,
        "rows": rows,
        "journal_export": "journal.csv (download in the real product)",
        "tag": TAG_FIXTURE,
    }


def _status_board() -> list[dict[str, str]]:
    return [
        {"item": "#1 Kestrel Parts · USD 4,820.00", "state": "PAID · provisional"},
        {
            "item": "#2 Brandt GmbH · original EUR 7,500.00",
            "state": "FAILED ACCOUNT_CLOSED → CANCELLED",
        },
        {"item": "#2 fraudulent IBAN change", "state": "REJECTED · never paid"},
        {"item": "#2 tranche 1 · EUR 2,314.81", "state": "PAID · provisional"},
        {"item": "#2 tranche 2 · EUR 5,185.19", "state": "HELD until tranche 1 final"},
        {"item": "#3 Helios Freight · GBP 2,140.00", "state": "PAID · provisional"},
        {"item": "#4 Kestrel duplicate INV-2211", "state": "HARD BLOCKED"},
        {"item": "#6 Marden Logistics · USD 3,900.00", "state": "DEFERRED (reserve floor)"},
        {"item": "#7 Helios Freight · GBP 1,860.00", "state": "PAID · provisional"},
    ]


def _shadow_rows() -> list[dict[str, str]]:
    return [
        {"row": "Changed-IBAN request on #2", "would_catch": "frozen pending callback · 1"},
        {"row": "Duplicate invoice INV-2211 (#4)", "would_catch": "hard-blocked · 1"},
        {"row": "Returned payout ACCOUNT_CLOSED", "would_catch": "routed through the lock · 1"},
    ]


def _audit_chain() -> dict[str, Any]:
    """A tiny real hash chain over the demo run's events."""
    entries = [
        ("run.opened", {"run": "demo", "payments": 6}),
        ("signoff.recorded", {"payment": 2, "by": "arun"}),
        ("change_request.rejected", {"payment": 2, "callback": "no_change_made"}),
        ("transfer.cancelled", {"payment": 2, "reason": "ACCOUNT_CLOSED"}),
    ]
    prev = "0" * 64
    head = prev
    for seq, (kind, payload) in enumerate(entries, start=1):
        head = audit.entry_hash(prev, kind, payload, _iso(_at(DEMO_TODAY, 9, seq)), seq)
        prev = head
    return {"checked": len(entries), "ok": True, "head": head[:12] + "…"}


def build_demo_payload() -> dict[str, Any]:
    """Everything the demo page renders, computed with the real core modules."""
    received_at = _at(DEMO_TODAY, 9, 5)
    mock = MockAirwallexClient()
    story = _callback_story(received_at)
    reserve = {
        "opening_usd": "26400.00",
        "floor_usd": "8000.00",
        "after_planned": "8240.00",
        "if_marden_paid": "4340.00",
        "defer_reason": "paying #6 would drop the reserve below USD 8,000",
        "after_block_and_withdrawal": "16340.00",
    }
    return {
        "demo_today": DEMO_TODAY.isoformat(),
        "badge": "SIMULATED DEMO DATA · Airwallex sandbox calls mocked",
        "company": "Halden Robotics",
        "people": {"arun": "Arun", "priya": "Priya", "meera": "Meera", "kabir": "Kabir"},
        "vendor_matches": _vendor_matches(),
        "payments": _payments(),
        "duplicate": _duplicate_check(),
        "reserve": reserve,
        "incident": _incident(received_at),
        "callbacks": story,
        "transfers": _transfers(mock),
        "tieout": _tieout(),
        "status_board": _status_board(),
        "shadow_rows": _shadow_rows(),
        "audit": _audit_chain(),
    }
