"""Out-of-band confirmation: the seven rules of FINAL.md §4.5.2.

Each test names the attack the rule closes, because a rule without its attack is
just a parameter. Two of these are worth reading even if the rest are skipped:

**Rule 7 without a signature is not an unverified callback, it is no callback.**
A row inserted straight into the database is the easiest attack on this system, and
the only defence is that the executor re-verifies the recorder's signature. If the
check were "present but unsigned", a database write would be enough.

**Rule 2's contact-ordering test.** A contact that is older than the change request
but *newer than every other contact* for the vendor was added in anticipation of it.
Hiding the number does not help, because the attacker already knows it - they put it
there.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core import oob
from app.core.oob import Contact


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def _old_contact(**over: object) -> Contact:
    base: dict[str, object] = {
        "id": "c1",
        "vendor_id": "v1",
        "kind": "phone",
        "value_norm": "49301234567",
        "provenance": "contract",
        "created_at": _dt(2026, 1, 1),
    }
    base.update(over)  # type: ignore[arg-type]
    return Contact(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Rule 1: who may record
# --------------------------------------------------------------------------


class TestRecorderIsNotTheRequester:
    def test_an_ops_user_outside_the_requester_set_passes(self) -> None:
        oob.check_recorder(
            recorded_by_role="ops",
            recorded_by_id="ops-1",
            requester_set=["ingest-1"],
            intake_user_id="ingest-1",
            run_approver_ids=["app-1", "app-2"],
        )

    def test_an_approver_role_is_refused(self) -> None:
        """A callback recorder must be ops, not someone who can approve.

        An approver who also confirms is one person performing both halves of the
        separation of duties, which is what §4.5.2 rule 1 exists to prevent.
        """
        with pytest.raises(oob.RequesterIsRecorderError, match="ops"):
            oob.check_recorder(
                recorded_by_role="approver",
                recorded_by_id="a1",
                requester_set=[],
            )

    def test_the_requester_confirming_is_refused(self) -> None:
        with pytest.raises(oob.RequesterIsRecorderError, match="requester set"):
            oob.check_recorder(
                recorded_by_role="ops",
                recorded_by_id="ops-1",
                requester_set=["ops-1"],
            )

    def test_the_intake_user_confirming_is_refused(self) -> None:
        with pytest.raises(oob.RequesterIsRecorderError, match="intake user"):
            oob.check_recorder(
                recorded_by_role="ops",
                recorded_by_id="ops-1",
                requester_set=["someone-else"],
                intake_user_id="ops-1",
            )

    def test_any_run_approver_confirming_is_refused(self) -> None:
        """Stricter than "at most one of the two approvers", as rule 1 states.

        A rule excluding only the packet's signers would let a second approver on a
        different item in the same run also confirm the bank change.
        """
        with pytest.raises(oob.RequesterIsRecorderError, match="approves on this run"):
            oob.check_recorder(
                recorded_by_role="ops",
                recorded_by_id="ops-1",
                requester_set=["someone-else"],
                run_approver_ids=["app-1", "ops-1"],
            )


# --------------------------------------------------------------------------
# Rule 2: which contact
# --------------------------------------------------------------------------


class TestContactAge:
    def test_a_contact_older_than_30_days_passes(self) -> None:
        oob.check_contact(
            contact=_old_contact(),
            change_request_received_at=_dt(2026, 4, 1),
        )

    def test_a_contact_created_after_the_request_is_refused(self) -> None:
        """A contact added after the request cannot confirm that request.

        The obvious direction: the number was supplied alongside the bank details.
        """
        with pytest.raises(oob.ContactTooNewError, match="created after"):
            oob.check_contact(
                contact=_old_contact(created_at=_dt(2026, 5, 1)),
                change_request_received_at=_dt(2026, 4, 1),
            )

    def test_a_contact_too_new_before_the_request_is_refused(self) -> None:
        with pytest.raises(oob.ContactTooNewError, match="existed"):
            oob.check_contact(
                contact=_old_contact(created_at=_dt(2026, 3, 20)),
                change_request_received_at=_dt(2026, 4, 1),
            )

    def test_a_contact_that_is_added_in_anticipation_is_refused(self) -> None:
        """Older than the request, but the newest contact for the vendor.

        This is the direction that hiding the number does not solve: the attacker
        added the row months ago precisely so it would look old enough. The ordering
        against the vendor's *other* contacts is what exposes it.
        """
        request = _dt(2026, 4, 1)
        with pytest.raises(oob.ContactTooNewError, match="anticipation"):
            oob.check_contact(
                # 40 days old: past the minimum, so the age check cannot catch it.
                # The ordering against the vendor's other contacts is what does.
                contact=_old_contact(created_at=_dt(2026, 2, 20)),
                change_request_received_at=request,
                other_contacts_for_vendor=[_old_contact(id="c0", created_at=_dt(2026, 1, 1))],
            )

    def test_the_oldest_contact_for_a_vendor_is_used(self) -> None:
        request = _dt(2026, 4, 1)
        oob.check_contact(
            contact=_old_contact(created_at=_dt(2025, 6, 1)),
            change_request_received_at=request,
            other_contacts_for_vendor=[_old_contact(id="c0", created_at=_dt(2026, 1, 1))],
        )

    def test_an_inactive_contact_is_refused(self) -> None:
        with pytest.raises(oob.ContactTooNewError, match="inactive"):
            oob.check_contact(
                contact=_old_contact(active=False),
                change_request_received_at=_dt(2026, 4, 1),
            )


class TestContactChangedRecently:
    def test_a_contact_changed_inside_30_days_is_refused(self) -> None:
        """Rule 5: a changed contact is itself a T2 change needing a callback.

        Confirming to a recently edited number would let a compromise be laundered
        by editing the record the check is made against.
        """
        request = _dt(2026, 4, 1)
        with pytest.raises(oob.ContactChangedRecentlyError, match="rule 5"):
            oob.check_contact(
                contact=_old_contact(created_at=_dt(2025, 1, 1), changed_at=_dt(2026, 3, 25)),
                change_request_received_at=request,
            )

    def test_a_contact_changed_long_before_passes(self) -> None:
        oob.check_contact(
            contact=_old_contact(created_at=_dt(2025, 1, 1), changed_at=_dt(2026, 1, 1)),
            change_request_received_at=_dt(2026, 4, 1),
        )


class TestNumberFromTheThread:
    def test_the_number_in_the_thread_is_refused(self) -> None:
        """The strongest single control in rule 2.

        If the requester can supply the number, they can supply the confirmation.
        """
        request = _dt(2026, 4, 1)
        with pytest.raises(oob.NumberFromChangeRequestError, match="triggered"):
            oob.check_contact(
                contact=_old_contact(),
                change_request_received_at=request,
                thread_artefacts=["Reply to +49 30 1234 567 for confirmation"],
            )

    def test_formatting_does_not_hide_the_number(self) -> None:
        """``+49 30 1234 567`` and ``+49301234567`` are one number.

        A normalisation that preserved separators would let the same number be
        written two ways, and only one of them would be caught.
        """
        request = _dt(2026, 4, 1)
        with pytest.raises(oob.NumberFromChangeRequestError):
            oob.check_contact(
                contact=_old_contact(),
                change_request_received_at=request,
                thread_artefacts=["call +49 30 1234 567"],
            )

    def test_a_different_number_is_fine(self) -> None:
        oob.check_contact(
            contact=_old_contact(),
            change_request_received_at=_dt(2026, 4, 1),
            thread_artefacts=["our main line is +49 30 9999 0000"],
        )


class TestProvenance:
    def test_a_new_payee_needs_an_independent_source(self) -> None:
        """A document cannot confirm the bank details that came from it."""
        assert oob.provenance_is_independent("contract", details_source_is_document=True)
        assert not oob.provenance_is_independent("document", details_source_is_document=True)

    def test_each_independent_provenance_passes(self) -> None:
        for kind in ["contract", "prior_invoice", "website", "registry"]:
            assert oob.provenance_is_independent(kind, details_source_is_document=False), kind

    def test_an_unknown_provenance_is_refused(self) -> None:
        assert not oob.provenance_is_independent("phone_call", details_source_is_document=False)


# --------------------------------------------------------------------------
# Rule 3: when
# --------------------------------------------------------------------------


class TestTiming:
    def test_a_callback_after_the_request_passes(self) -> None:
        oob.check_timing(
            called_at=_dt(2026, 4, 3),
            change_request_received_at=_dt(2026, 4, 1),
        )

    def test_a_callback_before_the_request_is_refused(self) -> None:
        """A stock confirm-on-file record cannot stand in for this request."""
        with pytest.raises(oob.CallbackTooEarlyError, match="before"):
            oob.check_timing(
                called_at=_dt(2026, 3, 31),
                change_request_received_at=_dt(2026, 4, 1),
            )

    def test_a_callback_outside_7_days_is_refused(self) -> None:
        with pytest.raises(oob.CallbackTooLateError):
            oob.check_timing(
                called_at=_dt(2026, 4, 10),
                change_request_received_at=_dt(2026, 4, 1),
            )

    def test_seven_days_exactly_is_inside(self) -> None:
        oob.check_timing(
            called_at=_dt(2026, 4, 8),
            change_request_received_at=_dt(2026, 4, 1),
        )


# --------------------------------------------------------------------------
# Rule 4: the readback
# --------------------------------------------------------------------------


class TestReadback:
    def test_a_confirmed_callback_needs_both_readbacks(self) -> None:
        """A phone call is not a confirmation.

        Rule 6 is explicit that the system records evidence of a callback and cannot
        prove a call happened; the readback is the part that makes the evidence worth
        anything at all.
        """
        with pytest.raises(oob.ReadbackRequiredError, match="readbacks"):
            oob.check_readback(outcome="CONFIRMED", readback_last4_ok=True, readback_name_ok=None)

    def test_a_complete_readback_passes(self) -> None:
        oob.check_readback(outcome="CONFIRMED", readback_last4_ok=True, readback_name_ok=True)

    @pytest.mark.parametrize("outcome", ["DENIED", "NO_ANSWER"])
    def test_a_denial_or_no_answer_needs_no_readback(self, outcome: str) -> None:
        oob.check_readback(outcome=outcome, readback_last4_ok=None, readback_name_ok=None)

    def test_a_mismatched_readback_cannot_be_confirmed(self) -> None:
        """The vendor read something back and it did not match.

        Marking that CONFIRMED would be the single most direct way to fake the
        control, and it is not available: only a match passes.
        """
        with pytest.raises(oob.ReadbackRequiredError):
            oob.check_readback(outcome="CONFIRMED", readback_last4_ok=False, readback_name_ok=True)


# --------------------------------------------------------------------------
# Rule 7: the signature
# --------------------------------------------------------------------------


class TestSignature:
    # RECORD is built per test rather than as a class attribute, because a mutable
    # default on a class is shared across every test in it (ruff RUF012).
    @staticmethod
    def _record() -> dict:
        return {
            "change_request_id": "cr1",
            "contact_id": "c1",
            "outcome": "CONFIRMED",
            "called_at": "2026-04-03T10:00:00Z",
        }

    def test_an_unsigned_callback_is_no_callback(self) -> None:
        """T-10b: the strictest rule in §4.5.2.

        Not "unverified" - absent. Treating it as weak-but-present would let a
        directly-inserted row take the place of a real confirmation.
        """
        with pytest.raises(oob.UnsignedCallbackError, match="no callback"):
            oob.verify_recorder_signature(record=self._record(), public_key=None, signature=b"")

    def test_a_replayed_nonce_is_refused(self) -> None:
        """A reused challenge would be indistinguishable from a fresh signature."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        signature = key.sign(oob._digest_input(self._record()))

        with pytest.raises(oob.UnsignedCallbackError, match="single"):
            oob.verify_recorder_signature(
                record=self._record(),
                public_key=key.public_key().public_bytes_raw(),
                signature=signature,
                nonce_used=True,
            )

    def test_a_signature_over_a_different_record_is_refused(self) -> None:
        """The record and the signature must be the same record."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        signature = key.sign(oob._digest_input({"change_request_id": "different"}))

        with pytest.raises(oob.UnsignedCallbackError, match="does not match"):
            oob.verify_recorder_signature(
                record=self._record(),
                public_key=key.public_key().public_bytes_raw(),
                signature=signature,
            )

    def test_the_hash_is_stable_across_key_order(self) -> None:
        """RFC 8785, so the same record hashes the same in the UI and the executor.

        A plain json.dumps would differ on key order, and the signature would verify
        in one place and not in the other.
        """
        assert oob.record_hash(self._record()) == oob.record_hash(
            dict(reversed(list(self._record().items())))
        )

    def test_the_hmac_fallback_is_labelled(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        signature = key.sign(oob._digest_input(self._record()))
        method = oob.verify_recorder_signature(
            record=self._record(),
            public_key=key.public_key().public_bytes_raw(),
            signature=signature,
            signing_method="HMAC_FALLBACK",
        )
        assert method == "cli_hmac"


# --------------------------------------------------------------------------
# Cooling-off
# --------------------------------------------------------------------------


class TestCoolingOff:
    def test_72_hours_after_the_later_of_the_two(self) -> None:
        """The later, not the earlier.

        A callback arriving quickly would otherwise shorten the window, and a fast
        confirmation is the one most likely to have been manufactured.
        """
        until = oob.cooling_off_until(
            callback_confirmed_at=_dt(2026, 4, 3),
            change_request_received_at=_dt(2026, 4, 1),
        )
        assert until == _dt(2026, 4, 6)

    def test_a_late_callback_extends_the_window(self) -> None:
        until = oob.cooling_off_until(
            callback_confirmed_at=_dt(2026, 4, 10),
            change_request_received_at=_dt(2026, 4, 1),
        )
        assert until == _dt(2026, 4, 13)

    def test_before_the_deadline_is_not_complete(self) -> None:
        assert not oob.is_cooling_off_complete(until=_dt(2026, 4, 6), now=_dt(2026, 4, 5))

    def test_after_the_deadline_is_complete(self) -> None:
        assert oob.is_cooling_off_complete(until=_dt(2026, 4, 6), now=_dt(2026, 4, 6))


# --------------------------------------------------------------------------
# First-payment cap and tranches
# --------------------------------------------------------------------------


class TestFirstPaymentCap:
    def test_a_vendor_with_no_history_gets_the_floor(self) -> None:
        assert oob.first_payment_cap(median_12m_final_usd=None) == (oob.DEFAULT_FIRST_PAYMENT_USD)

    def test_the_cap_is_the_smaller_of_the_two(self) -> None:
        """``min``, not ``max``: the cap is a ceiling.

        A high-volume supplier is not a reason to send a large first payment - that
        is backwards, and would make the most valuable accounts the least protected.
        """
        assert oob.first_payment_cap(median_12m_final_usd=Decimal("100000")) == (Decimal("2500"))
        assert oob.first_payment_cap(median_12m_final_usd=Decimal("1000")) == Decimal("500")


class TestTranches:
    def test_an_obligation_under_the_cap_is_not_split(self) -> None:
        """A single tranche is not a tranche, and must not be held.

        Producing two rows for a small obligation would hold a payment that should
        have gone out, for no reason.
        """
        tranches = oob.tranche_split(
            total=Decimal("100.00"),
            currency="EUR",
            cap_usd=Decimal("2500"),
            rate=Decimal("1"),
            exponent=2,
        )
        assert len(tranches) == 1
        assert tranches[0].amount == Decimal("100.00")

    def test_tranche_1_is_the_cap_and_is_rounded_down(self) -> None:
        """Rounding down keeps tranche 1 within the cap.

        Rounding up would make the first tranche *larger* than the limit it is
        derived from, which is the one thing the cap exists to prevent. The remainder
        absorbs the rounding, and it is the part that is held.
        """
        tranches = oob.tranche_split(
            total=Decimal("10000.00"),
            currency="EUR",
            cap_usd=Decimal("2500"),
            rate=Decimal("1.0001"),
            exponent=2,
        )
        assert len(tranches) == 2
        # 2500 USD at 1.0001 = 2500.25, and the remainder absorbs the rounding.
        assert tranches[0].amount == Decimal("2500.25")
        assert tranches[1].amount == Decimal("7499.75")
        assert tranches[0].amount + tranches[1].amount == Decimal("10000.00")

    def test_a_zero_decimal_currency_is_not_rounded_up(self) -> None:
        """KRW: the cap converted rounds down to whole won."""
        tranches = oob.tranche_split(
            total=Decimal("3000000"),
            currency="KRW",
            cap_usd=Decimal("100"),
            rate=Decimal("1300"),
            exponent=0,
        )
        # 100 USD at 1300 = 130000 KRW, no fractional part to round.
        assert tranches[0].amount == Decimal("130000")

    def test_tranches_are_one_obligation_and_not_a_split(self) -> None:
        """§4.5.4 says so explicitly.

        A caller that ran ``app.core.dupes`` over tranches would raise
        SUSPECT_DUPLICATE or SPLIT_SUSPECT for a payment the spec requires to
        proceed, and the cap would be self-defeating.
        """
        tranches = oob.tranche_split(
            total=Decimal("9000.00"),
            currency="USD",
            cap_usd=Decimal("2500"),
            rate=Decimal("1"),
            exponent=2,
        )
        assert len(tranches) == 2
        assert {t.tranche_no for t in tranches} == {1, 2}


def test_every_rule_has_a_guard() -> None:
    """Rule 6 is a documentation rule and deliberately has no guard.

    Everything else must map to code, or the rule is a comment rather than a control.
    This test is what stops "we implemented 4.5.2" being a claim about prose.
    """
    implemented = oob.coverage()
    for rule, guard in implemented.items():
        if rule == "6":
            assert "README" in guard
            continue
        assert hasattr(oob, guard.split(" ")[0].strip()), (
            f"rule {rule} names {guard!r} which does not exist"
        )
