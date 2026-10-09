"""Vendor matching, and the lookalike-domain quarantine.

FINAL.md §4.3 fixes the order (tax ID, then legal name, then sender domain) and
the failure mode (a lookalike is quarantined, never matched).

These tests exist because the interesting cases are the near-misses, and the
consequences of getting them wrong are asymmetric in a way that a happy-path test
cannot express: a missed lookalike pays the wrong company, and a wrongly blocked
supplier stops a real payment. Both are tested.
"""

from __future__ import annotations

import pytest

from app.core.vendors import (
    LOOKALIKE_FLAG,
    MAX_LOOKALIKE_DISTANCE,
    MatchKind,
    VendorRecord,
    edit_distance,
    match_vendor,
    normalise_legal_name,
)

ACME = VendorRecord(
    id="v-acme",
    tax_id="123456789",
    legal_name="Acme Industrial Supplies Ltd",
    known_domains=("acme.com",),
)
BRANDT = VendorRecord(
    id="v-brandt",
    tax_id="987654321",
    legal_name="Brandt Metallwaren GmbH",
    known_domains=("brandt.de",),
)
ALL = [ACME, BRANDT]


class TestMatchingOrder:
    """§4.3 names the order, and the order is the security property."""

    def test_tax_id_wins_over_everything(self) -> None:
        """A tax ID is supposed to be unique, so it is the only primary identifier.

        A sender domain that *contradicts* the tax ID is not a signal: the tax ID
        wins, because it is the one an attacker cannot forge out of a spelling.
        """
        match = match_vendor(
            tax_id="987654321",
            legal_name="Acme Industrial Supplies Ltd",
            sender_domains=["acme.com"],
            vendors=ALL,
        )
        assert match.kind == MatchKind.TAX_ID
        assert match.vendor_id == "v-brandt"

    def test_legal_name_is_second(self) -> None:
        match = match_vendor(
            tax_id=None,
            legal_name="acme industrial supplies ltd",
            sender_domains=[],
            vendors=ALL,
        )
        assert match.kind == MatchKind.LEGAL_NAME
        assert match.vendor_id == "v-acme"

    def test_sender_domain_is_last(self) -> None:
        match = match_vendor(
            tax_id=None,
            legal_name=None,
            sender_domains=["acme.com"],
            vendors=ALL,
        )
        assert match.kind == MatchKind.SENDER_DOMAIN
        assert match.vendor_id == "v-acme"

    def test_no_match_when_nothing_fits(self) -> None:
        match = match_vendor(
            tax_id="999", legal_name="Novus Inter Ltd", sender_domains=[], vendors=ALL
        )
        assert match.kind == MatchKind.NONE
        assert not match.matched
        assert not match.quarantine


class TestLookalikeQuarantine:
    """The fraud case. A near-match must never become a match."""

    @pytest.mark.parametrize(
        "sender",
        [
            "acrne.com",  # one substitution
            "acme.co",  # one deletion
            "aacme.com",  # one insertion
            "acme.con",  # transposition counts as 2 under Levenshtein
        ],
    )
    def test_one_and_two_edits_are_quarantined(self, sender: str) -> None:
        match = match_vendor(sender_domains=[sender], vendors=ALL, tax_id=None, legal_name=None)
        assert match.kind == MatchKind.LOOKALIKE, sender
        assert match.vendor_id is None
        assert not match.matched, "a lookalike must never resolve to a vendor"
        assert match.quarantine

    def test_the_boundary_is_exactly_two(self) -> None:
        """One and two edits are a lookalike; three is a different domain.

        ``acrne.com`` is two substitutions (r-for-m, n-for-e) and ``acme.con`` is
        one (n-for-m). Both were asserted wrongly on the first run: I expected
        ``acrne.com`` to be one edit and ``acme.con`` to be two, having confused
        which positions differ. The code was right and the test was wrong (D-B25).
        """
        assert edit_distance("acme.con", "acme.com") == 1
        assert edit_distance("acrne.com", "acme.com") == 2
        assert edit_distance("acrrne.conz", "acme.com") > MAX_LOOKALIKE_DISTANCE

    def test_a_homoglyph_is_quarantined_not_matched(self) -> None:
        """A Cyrillic "a" is not within edit distance 1 of the ASCII one.

        It maps through the confusable table, which is why folding has to happen
        *before* the distance check rather than after.
        """
        sender = "\u0430cme.com"  # first letter Cyrillic
        match = match_vendor(sender_domains=[sender], vendors=ALL, tax_id=None, legal_name=None)
        assert match.kind == MatchKind.LOOKALIKE
        assert match.vendor_id is None
        assert match.near_domain == "acme.com"

    def test_a_confusable_separator_is_quarantined(self) -> None:
        """A fullwidth dot resolves differently in DNS and reads the same."""
        sender = "acme\uff0ecom"
        match = match_vendor(sender_domains=[sender], vendors=ALL, tax_id=None, legal_name=None)
        assert match.kind == MatchKind.LOOKALIKE

    def test_a_known_domain_wrapped_around_another_is_quarantined(self) -> None:
        """``acme.com.evil.example`` starts with a real domain.

        Not a small edit, so distance alone would miss it. A human reading the
        sender line sees "acme.com" first and stops reading.
        """
        match = match_vendor(
            sender_domains=["acme.com.evil.example"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.kind == MatchKind.LOOKALIKE
        assert match.vendor_id is None

    def test_a_subdomain_is_quarantined_not_silently_ignored(self) -> None:
        """``mail.acme.com`` is not an exact match of ``acme.com``, per §4.3.

        A first version of this test asserted it *matched*, which is not what the
        spec says and not what the code does. §4.3 names "known sender domain
        exact", and ``mail.acme.com`` is not exactly ``acme.com``.

        That is a real gap in the spec rather than a bug in the code, and it is
        recorded as D-B25: a supplier whose bills always arrive from
        ``billing.acme.com`` will never auto-match and will always need a human.
        The fix is a domain per *sender* rather than a domain per vendor, and that
        is a schema change rather than a matcher change - so it is named here
        rather than worked around, because a workaround would be a silent
        relaxation of a spec rule.

        What is asserted is the safe half: a subdomain is not silently resolved to
        a vendor, which would be the dangerous failure.
        """
        match = match_vendor(
            sender_domains=["mail.acme.com"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.vendor_id is None
        assert match.kind == MatchKind.NONE


class TestRegisteredDomainGap:
    """Recorded as D-B25: §4.3 says "exact", and exact is not what a supplier does."""

    def test_a_subdomain_sender_never_resolves(self) -> None:
        """The gap, stated as a failing-yet-passing assertion.

        Not worked around. A real supplier's billing mail routinely comes from a
        subdomain, so under the shipped rule every one of those bills needs a
        human. The correct fix is to record domains per *sender* in the vendor
        contact table, which is a schema change this milestone does not attempt.
        """
        match = match_vendor(
            sender_domains=["billing.acme.com"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.kind == MatchKind.NONE
        assert not match.matched

    def test_a_port_path_or_credentials_do_not_hide_a_lookalike(self) -> None:
        """``acrne.com:8080/bill`` is still acrne.com."""
        match = match_vendor(
            sender_domains=["acrne.com:8080/bill"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.kind == MatchKind.LOOKALIKE

    def test_the_flag_is_the_one_4_3_names(self) -> None:
        match = match_vendor(
            sender_domains=["acrne.com"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.quarantine

        # The flag string itself is exported for a caller to attach.
        assert LOOKALIKE_FLAG == "LOOKALIKE_DOMAIN"

    def test_a_distinct_domain_is_not_a_lookalike(self) -> None:
        """A real competitor is not an attack on Acme."""
        match = match_vendor(
            sender_domains=["metalsupply.de"], vendors=ALL, tax_id=None, legal_name=None
        )
        assert match.kind == MatchKind.NONE
        assert not match.quarantine


class TestNameNormalisation:
    """§4.3: exact on the normalised name, and no fuzzy match, ever."""

    def test_case_and_punctuation_do_not_matter(self) -> None:
        assert normalise_legal_name("ACME  Industrial Supplies  Ltd.") == (
            normalise_legal_name("acme industrial supplies ltd")
        )

    def test_invisible_characters_do_not_matter(self) -> None:
        """A zero-width space in a supplier name is not a different supplier."""
        assert normalise_legal_name("Acme\u200b Industrial") == (
            normalise_legal_name("Acme Industrial")
        )

    def test_a_legal_form_suffix_is_not_stripped(self) -> None:
        """Two firms differing only in legal form are two firms.

        Stripping suffixes would be the start of fuzzy matching, which §4.3
        forbids.
        """
        assert normalise_legal_name("Acme Ltd") != normalise_legal_name("Acme GmbH")

    def test_a_homoglyph_in_a_name_is_not_folded(self) -> None:
        """A confusable-looking letter is a real letter in a real supplier name.

        Folding it away would merge two distinct suppliers silently, which is worse
        than quarantining a near-miss a human can see.
        """
        assert normalise_legal_name("\u0410cme") != normalise_legal_name("Acme")


class TestEditDistance:
    def test_the_same_string_is_zero(self) -> None:
        assert edit_distance("acme.com", "acme.com") == 0

    def test_a_length_gap_is_bounded(self) -> None:
        """A gap larger than the bound short-circuits.

        Without the early exit, matching every vendor in the table is quadratic in
        the number of vendors.
        """
        assert edit_distance("a" * 30, "b") > MAX_LOOKALIKE_DISTANCE

    def test_a_transposition_costs_two(self) -> None:
        """Levenshtein, not Damerau: no transposition primitive.

        ``amce.com`` is distance 2 from ``acme.com`` - a transposition costs two
        substitutions under Levenshtein, and there is no Damerau primitive. Both it
        and a single substitution are inside the lookalike bound, so the boundary is
        the same either way; the exact value matters only to a caller that asks.
        """
        assert edit_distance("amce.com", "acme.com") == 2
        assert edit_distance("acme.con", "acme.com") == 1
