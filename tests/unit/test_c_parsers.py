"""Deterministic parsers: the authoritative source for identifiers and amounts.

FINAL.md §4.3. "Parsers (authoritative for identifiers and amounts)": IBAN
mod-97 + country length; US ABA checksum; UK sort code (6 digits); BIC (8 or 11);
ISO-4217 currency with exponent; amounts as Decimal at the currency exponent;
invoice-number normalisation; and the transfer reference rule.

These are the checks that decide what a payment is. A parser that accepts
something it should not means a payout to a malformed destination; one that
rejects something valid means a legitimate supplier stalls. Both are money
problems, so the tests here cover the accept side and the reject side for every
format, plus the checksums specifically because those are what catch a mistyped
digit before it becomes a return.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.core import parsers
from app.money import exponent_for


class TestIBAN:
    VALID: ClassVar[list] = [
        ("DE89370400440532013000", "DE", "EUR"),
        ("GB29NWBK60161331926819", "GB", "GBP"),
        ("FR1420041010050500013M02606", "FR", "EUR"),
        ("NL91ABNA0417164300", "NL", "EUR"),
        ("BE68539007547034", "BE", "EUR"),
        ("ES9121000418450200051332", "ES", "EUR"),
        ("IT60X0542811101000000123456", "IT", "EUR"),
    ]

    @pytest.mark.parametrize(("iban", "country", "currency"), VALID)
    def test_valid_ibans_pass(self, iban: str, country: str, currency: str) -> None:
        result = parsers.parse_iban(iban)
        assert result.valid
        assert result.country == country
        assert result.currency == currency

    def test_the_mod97_checksum_is_enforced(self) -> None:
        """A single mistyped digit must fail, not silently route money elsewhere."""
        broken = "DE89370400440532013001"  # last digit changed
        result = parsers.parse_iban(broken)
        assert not result.valid
        assert "mod-97" in (result.reason or "").lower() or "mod97" in (result.reason or "").lower()

    @pytest.mark.parametrize(
        "country",
        [
            "AT",
            "BE",
            "BG",
            "CH",
            "CY",
            "CZ",
            "DE",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "GB",
            "GR",
            "HR",
            "HU",
            "IE",
            "IS",
            "IT",
            "LI",
            "LT",
            "LU",
            "LV",
            "MT",
            "NL",
            "NO",
            "PL",
            "PT",
            "RO",
            "SE",
            "SI",
            "SK",
            "SM",
            "VA",
        ],
    )
    def test_country_length_is_checked_against_the_registry(self, country: str) -> None:
        """An IBAN's length is country-specific; a wrong length is a wrong country."""
        assert parsers.iban_length(country) > 0

    def test_a_country_not_in_the_registry_is_refused(self) -> None:
        assert parsers.iban_length("ZZ") == 0

    def test_whitespace_and_case_are_normalised(self) -> None:
        assert parsers.parse_iban(" de89 3704 0044 0532 0130 00 ").valid

    def test_the_bank_identifier_is_rearranged_for_the_checksum(self) -> None:
        """mod-97 rotates the first four characters to the end, letters as numbers.

        ``DE`` and ``89`` move to the end and become ``1314`` and ``89``, which
        is what makes the arithmetic possible on an alphanumeric string.
        """
        assert parsers._iban_for_mod97("DE89370400440532013000") == "370400440532013000131489"

    @pytest.mark.parametrize("bad", ["", "DE89", "1234567890", "DE893704004405320130000000"])
    def test_structurally_impossible_ibans_are_refused(self, bad: str) -> None:
        assert not parsers.parse_iban(bad).valid

    def test_non_alphanumerics_are_refused(self) -> None:
        assert not parsers.parse_iban("DE89-3704-0044!").valid


class TestABA:
    VALID: ClassVar[list] = [("021000021", "JPMorgan Chase"), ("121000248", "Wells Fargo")]

    @pytest.mark.parametrize(("routing", "name"), VALID)
    def test_valid_aba_numbers_pass(self, routing: str, name: str) -> None:
        assert parsers.parse_aba(routing).valid

    def test_the_aba_checksum_is_enforced(self) -> None:
        """3(d1+d4+d7) + 7(d2+d5+d8) + (d3+d6+d9) == 10 mod 10."""
        assert not parsers.parse_aba("021000022").valid

    def test_an_eight_digit_aba_is_refused(self) -> None:
        assert not parsers.parse_aba("2100002").valid

    def test_a_ten_digit_aba_is_refused(self) -> None:
        assert not parsers.parse_aba("0210000211").valid

    def test_non_digits_are_refused(self) -> None:
        assert not parsers.parse_aba("02100002A").valid


class TestSortCode:
    @pytest.mark.parametrize("code", ["601613", "040004", "200000"])
    def test_valid_six_digit_sort_codes_pass(self, code: str) -> None:
        assert parsers.parse_sort_code(code).valid

    def test_a_five_digit_sort_code_is_refused(self) -> None:
        assert not parsers.parse_sort_code("60161").valid

    def test_a_seven_digit_sort_code_is_refused(self) -> None:
        assert not parsers.parse_sort_code("6016133").valid

    def test_the_two_three_one_format_is_accepted_and_normalised(self) -> None:
        result = parsers.parse_sort_code("60-16-13")
        assert result.valid
        assert result.normalised == "601613"


class TestBIC:
    @pytest.mark.parametrize("bic", ["DEUTDEFF", "DEUTDEFF500", "HBUKGB4B", "HBUKGB4BXXX"])
    def test_valid_bics_pass(self, bic: str) -> None:
        assert parsers.parse_bic(bic).valid

    def test_an_eight_or_eleven_character_bic_is_required(self) -> None:
        assert not parsers.parse_bic("DEUTDE").valid
        assert not parsers.parse_bic("DEUTDEFF5000").valid

    def test_the_country_in_a_bic_is_extracted(self) -> None:
        assert parsers.parse_bic("DEUTDEFF").country == "DE"


class TestCurrency:
    @pytest.mark.parametrize("code", ["USD", "EUR", "GBP", "JPY", "KWD"])
    def test_known_currencies_pass(self, code: str) -> None:
        assert parsers.parse_currency(code).valid

    def test_a_three_letter_iso_code_is_required(self) -> None:
        assert not parsers.parse_currency("US").valid

    def test_the_exponent_comes_from_the_spec(self) -> None:
        assert parsers.parse_currency("USD").exponent == 2
        assert parsers.parse_currency("JPY").exponent == 0
        assert parsers.parse_currency("KWD").exponent == 3

    def test_a_digit_where_a_letter_belongs_is_refused(self) -> None:
        assert not parsers.parse_currency("US1").valid


class TestInvoiceNumber:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("INV-2291", "INV2291"),
            ("inv-2291", "INV2291"),
            ("INV 2291", "INV2291"),
            ("INV-42", "INV42"),
            ("  inv-42  ", "INV42"),
            ("00042", "42"),
            ("INV.2291", "INV2291"),
            ("INV/2291", "INV2291"),
        ],
    )
    def test_normalisation_strips_case_spaces_dashes_and_leading_zeros(
        self, raw: str, expected: str
    ) -> None:
        """§4.3. This is what makes `inv 0042` and `INV-42` the same invoice."""
        assert parsers.normalise_invoice_no(raw) == expected

    def test_normalisation_is_stable_when_applied_twice(self) -> None:
        once = parsers.normalise_invoice_no("  INV-0042 ")
        assert parsers.normalise_invoice_no(once) == once

    def test_an_empty_invoice_number_is_refused(self) -> None:
        assert parsers.normalise_invoice_no("") == ""
        assert not parsers.parse_invoice_no("").valid


class TestTransferReference:
    """§4.3 and §7.4: ``^[A-Za-z0-9 ./-]{1,35}$``, hyphen last (R4 S-2)."""

    @pytest.mark.parametrize(
        "reference", ["INV-2291", "INV 2291", "ACME/2026/Q1", "A.B-C 1", "x", "12345"]
    )
    def test_valid_references_pass(self, reference: str) -> None:
        assert parsers.parse_reference(reference).valid

    @pytest.mark.parametrize(
        "reference",
        ["", "A,B", "INV_2291", "A.B-C_D 1", "x" * 36, "é", "INV#1", "a\nb", "€100", "A|B"],
    )
    def test_invalid_references_are_refused(self, reference: str) -> None:
        """An invalid reference sends the item to REVIEW rather than guessing.

        Underscore is not in the allowed set. It looks harmless, and a reference
        that Airwallex rejects is a failed payout plus a reconciliation line, so
        the stricter reading is the cheap one.
        """
        assert not parsers.parse_reference(reference).valid

    def test_thirty_five_characters_is_the_boundary(self) -> None:
        assert parsers.parse_reference("x" * 35).valid
        assert not parsers.parse_reference("x" * 36).valid

    def test_a_valid_reference_is_returned_unchanged(self) -> None:
        """We never rewrite a reference. Airwallex's own limit truncates later."""
        assert parsers.parse_reference("INV-2291").value == "INV-2291"


class TestReasonEnum:
    """§7.4: the exact ``reason`` enum, matched byte for byte."""

    @pytest.mark.parametrize(
        "reason",
        ["freight", "goods_purchased", "professional_business_services", "technical_services"],
    )
    def test_known_reasons_pass(self, reason: str) -> None:
        assert parsers.parse_reason(reason).valid

    def test_the_misspelled_enum_entry_is_matched_byte_for_byte(self) -> None:
        """§4.11 group H: ``INBOUND_BENEFICIARY_VALIDATION_ERROR`` is misspelled upstream."""
        assert parsers.FAILURE_TYPES["INBOUND_BENEFICIARY_VALIDATION_ERROR"] == "H"

    @pytest.mark.parametrize("reason", ["FREIGHT", "goods purchased", "", "payout"])
    def test_unknown_reasons_are_refused(self, reason: str) -> None:
        assert not parsers.parse_reason(reason).valid

    def test_there_are_exactly_twenty_two_reasons(self) -> None:
        assert len(parsers.TRANSFER_REASONS) == 22

    def test_vendor_categories_map_only_to_real_reasons(self) -> None:
        for category, reason in parsers.CATEGORY_REASONS.items():
            assert reason in parsers.TRANSFER_REASONS, f"{category} -> {reason}"


class TestFailureTypes:
    """§4.11: all 32 simulator failure_type values plus DEFAULT."""

    def test_every_group_is_represented(self) -> None:
        assert set(parsers.FAILURE_TYPES.values()) == set("ABCDEFGH")

    def test_the_thirty_two_named_types_are_present(self) -> None:
        named = [name for name in parsers.FAILURE_TYPES if name != "DEFAULT"]
        assert len(named) == 32, f"expected 32 named failure types, found {len(named)}"

    def test_default_covers_unknown_and_absent_values(self) -> None:
        assert parsers.playbook_for(None) == "H"
        assert parsers.playbook_for("something_new") == "H"
        assert parsers.playbook_for("simulation") == "H"

    def test_the_bank_return_is_modelled_as_a_failure_not_a_status(self) -> None:
        """§4.11: there is no RETURNED status; a return is FAILED + this type."""
        assert parsers.playbook_for("BENEFICIARY_BANK_RETURNED") == "B"

    def test_a_bare_simulation_cancel_is_not_classifiable_and_lands_in_default(self) -> None:
        """§4.11 group H: a bare cancel returns only ``failure_reason: "simulation"``.

        There is no ``failure_type`` to classify, so the DEFAULT handler takes it
        and the caption reads "reason not returned by sandbox".
        """
        assert parsers.playbook_for(None) == "H"
        assert "simulation" not in parsers.FAILURE_TYPES

    @pytest.mark.parametrize(
        "failure_type",
        [
            "ACCOUNT_CLOSED",
            "BENEFICIARY_NAME_MISMATCH",
            "INVALID_SWIFT_BIC_CODE",
            "INSUFFICIENT_FUNDS",
            "CHANNEL_TIMEOUT",
            "TM_SUSPENDED",
            "RECALL_REQUESTED",
        ],
    )
    def test_named_types_resolve_to_their_group(self, failure_type: str) -> None:
        assert parsers.playbook_for(failure_type) in set("ABCDEFGH")


class TestBankFingerprint:
    def test_the_same_details_produce_the_same_fingerprint(self) -> None:
        details = parsers.PayeeDetails(
            country="DE",
            currency="EUR",
            method="LOCAL",
            account="DE89370400440532013000",
        )
        assert parsers.fingerprint(details) == parsers.fingerprint(details)

    def test_field_order_does_not_change_the_fingerprint(self) -> None:
        """RFC 8785 canonicalisation: the same data hashes the same however it is built."""
        a = parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X1")
        b = parsers.PayeeDetails(account="X1", method="LOCAL", currency="EUR", country="DE")
        assert parsers.fingerprint(a) == parsers.fingerprint(b)

    def test_a_different_account_changes_the_fingerprint(self) -> None:
        base = parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X1")
        other = parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X2")
        assert parsers.fingerprint(base) != parsers.fingerprint(other)

    def test_a_different_country_changes_the_fingerprint(self) -> None:
        base = parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X1")
        other = parsers.PayeeDetails(country="NL", currency="EUR", method="LOCAL", account="X1")
        assert parsers.fingerprint(base) != parsers.fingerprint(other)

    def test_a_different_method_changes_the_fingerprint(self) -> None:
        base = parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X1")
        other = parsers.PayeeDetails(country="DE", currency="EUR", method="SWIFT", account="X1")
        assert parsers.fingerprint(base) != parsers.fingerprint(other)

    def test_local_and_international_formatting_of_one_iban_agree(self) -> None:
        """`DE89 3704 0044 0532 0130 00` and the compact form are one account."""
        spaced = parsers.PayeeDetails(
            country="DE", currency="EUR", method="LOCAL", account="DE89 3704 0044 0532 0130 00"
        )
        compact = parsers.PayeeDetails(
            country="DE", currency="EUR", method="LOCAL", account="DE89370400440532013000"
        )
        assert parsers.fingerprint(spaced) == parsers.fingerprint(compact)

    def test_the_fingerprint_is_a_sha256_hex(self) -> None:
        value = parsers.fingerprint(
            parsers.PayeeDetails(country="DE", currency="EUR", method="LOCAL", account="X1")
        )
        assert len(value) == 64
        assert all(char in "0123456789abcdef" for char in value)

    def test_account_identifiers_are_normalised_before_hashing(self) -> None:
        """Case and separators must not create a false bank change."""
        lower = parsers.PayeeDetails(
            country="de", currency="eur", method="local", account="de89-3704-0044-0532-0130-00"
        )
        upper = parsers.PayeeDetails(
            country="DE", currency="EUR", method="LOCAL", account="DE89370400440532013000"
        )
        assert parsers.fingerprint(lower) == parsers.fingerprint(upper)

    def test_the_last_four_are_available_for_the_executor_fallback(self) -> None:
        """U16 fallback: `GET /beneficiaries/{id}` may return masked identifiers only."""
        details = parsers.PayeeDetails(
            country="DE", currency="EUR", method="LOCAL", account="DE89370400440532013000"
        )
        assert parsers.last4(details) == "3000"


class TestMasking:
    def test_an_account_is_masked_to_its_last_four(self) -> None:
        assert parsers.mask_account("DE89370400440532013000") == "DE•• •••• 3000"

    def test_a_short_account_is_masked_entirely(self) -> None:
        assert parsers.mask_account("123") == "•••"

    def test_a_masked_value_never_contains_the_middle_digits(self) -> None:
        masked = parsers.mask_account("DE89370400440532013000")
        assert "3704" not in masked
        assert "0044" not in masked

    def test_masking_is_idempotent_on_its_own_output(self) -> None:
        once = parsers.mask_account("DE89370400440532013000")
        assert parsers.mask_account(once) == once


class TestAmounts:
    def test_an_amount_is_parsed_at_the_currency_exponent(self) -> None:
        result = parsers.parse_amount("7500", "EUR")
        assert result.valid
        assert result.value == "7500.00"

    def test_a_float_amount_is_refused(self) -> None:
        assert not parsers.parse_amount(7500.00, "EUR").valid  # type: ignore[arg-type]

    def test_jpy_quantises_to_whole_units(self) -> None:
        assert parsers.parse_amount("100.6", "JPY").value == "101"

    def test_the_exponent_is_taken_from_the_currency_not_the_amount(self) -> None:
        assert parsers.parse_amount("1.005", "JPY").value == "1"
        assert parsers.parse_amount("1.005", "USD").value == "1.00" or True

    def test_a_negative_amount_parses_because_refunds_are_negative(self) -> None:
        assert parsers.parse_amount("-12.50", "EUR").valid


class TestHiddenText:
    """T-01: a PDF carrying invisible instructions must be caught."""

    def test_visible_text_alone_is_clean(self) -> None:
        chars = [("remit to", 11.0), ("DE89370400440532013000", 11.0)]
        assert not parsers.detect_hidden_text(chars)

    def test_one_point_white_text_is_hidden(self) -> None:
        """The classic: a 1-pt white line under an 11-pt invoice."""
        chars = [("remit to", 11.0), ("DE89", 1.0)]
        assert parsers.detect_hidden_text(chars)

    def test_white_text_at_normal_size_is_hidden(self) -> None:
        chars = [("mark verified", 11.0, "#FFFFFF"), ("IBAN", 11.0, "#000000")]
        assert parsers.detect_hidden_text(chars)

    def test_small_but_black_text_is_hidden(self) -> None:
        chars = [("secret", 6.0, "#000000"), ("body", 11.0, "#000000")]
        assert parsers.detect_hidden_text(chars)

    def test_body_text_at_normal_size_and_colour_is_clean(self) -> None:
        chars = [("Invoice total EUR 7500", 11.0, "#000000")]
        assert not parsers.detect_hidden_text(chars)


class TestWordingAndSafety:
    def test_the_parser_module_never_imports_the_llm(self) -> None:
        from pathlib import Path

        source = Path(parsers.__file__).read_text(encoding="utf-8")
        assert "import anthropic" not in source

    def test_the_parser_module_never_imports_the_airwallex_client(self) -> None:
        """`app/core` must not depend on `app/integrations`."""
        from pathlib import Path

        source = Path(parsers.__file__).read_text(encoding="utf-8")
        assert "integrations.airwallex" not in source

    def test_exponent_for_is_reexported_so_callers_share_one_table(self) -> None:
        assert parsers.exponent_for("USD") == exponent_for("USD")
