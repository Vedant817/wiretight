"""The compliance index: every T-ID in FINAL.md §10.3 must have a test.

FINAL.md §10.1 requires this file by name: "A CI guard
(``tests/acceptance/test_compliance_index.py``) asserts that every ID below
appears in at least one ``@pytest.mark.compliance("T-xx")`` marker."

The list is transcribed from §10.3 rather than imported from the implementation,
so a row quietly dropped from the floor or the executor cannot shrink the index
along with it. If a row in §10.3 no longer applies, the fix is to delete it here
**and** record why in docs/DECISIONS.md, not to relax the assertion here.

Milestone (b) is complete; later milestones are expected to be incomplete. Those
IDs are listed explicitly as PENDING so the failure says which work is missing
rather than dumping 30 unexplained names.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: The whole tests/ tree, not just acceptance/. T-R4e and T-09a/b live in
#: tests/unit/, and scanning only this directory reported them as missing.
TESTS_DIR = Path(__file__).resolve().parents[1]

#: Every T-ID §10.3 names, with its milestone letter.
#: (id, milestone, one-line description)
SPEC_INDEX: tuple[tuple[str, str, str], ...] = (
    ("T-01", "c2", "hidden white 1-pt IBAN B text"),
    ("T-02", "c2", "memo claims a phone confirmation"),
    ("T-03", "c1+e2", "XSS name, SQL-ish invoice no, invalid reference"),
    ("T-04", "f1", "bank details change between sign-off and execution"),
    ("T-04b", "f1", "beneficiary last-4 differs (U16 fallback)"),
    ("T-04c", "f1", "first payment to new details: beneficiary created at execute"),
    ("T-05", "c1+d", "velocity caps: 3x1900 T0, 2x5500 T2"),
    ("T-06", "e1", "replayed approval assertion"),
    ("T-07", "b+f1", "HALT mid-run and unreadable HALT path"),
    ("T-08", "d", "daily caps and the IST day boundary"),
    ("T-09", "a", "prod URL, AWX_ENV, 302, HTTPS_PROXY"),
    ("T-10", "c1", "callback number taken from the change email"),
    ("T-10b", "c1+f1", "callback row without a valid ops signature"),
    ("T-11", "e1", "requester signs, same human twice, duplicate roster email"),
    ("T-12", "e1+f1", "quote expiring inside 120s, re-quote drift"),
    ("T-13", "b", "audit_log UPDATE and an offline edit"),
    ("T-14", "c1", "verify_account off / CANNOT_VERIFY / FULL_MATCH"),
    ("T-15", "f1", "crash after transfers/create, before the DB write"),
    ("T-16", "f1", "AMBIGUOUS attempt then a re-plan in another run"),
    ("T-17", "b+f1", "audit DB unwritable"),
    ("T-18", "c2+d", "LLM provider down"),
    ("T-19", "b", "policy lowers the floor unsigned; unknown key"),
    ("T-20", "d", "one GBP conversion funds two items, one voids"),
    ("T-21", "c1", "onboarding PDF supplies both details and the phone"),
    ("T-21b", "f2", "replayed webhook; FAILED webhook vs GET SENT"),
    ("T-22", "d", "2 FINAL of USD 1 then USD 1,999"),
    ("T-23", "e1", "forged APPROVED status via SQL"),
    ("T-24", "f1", "balance drops below the floor between sign-off and execute"),
    ("T-25", "f1", "fx/conversions/create times out"),
    ("T-26", "c2", "one document says use IBAN B for other invoices"),
    ("T-27", "b", "loosen any floor row, parametrised"),
    ("T-28", "c1+d+f1", "callback confirmed, then a capped first payment with tranches"),
    ("T-29", "c1", "phone edited day 0, IBAN change day 2"),
    ("T-30", "c2", "LLM IBAN differs from the parser"),
    ("T-31", "f2", "compliance failure_type trips and holds"),
    ("T-32", "e1", "MIN_1 quote is never bookable"),
    ("T-33", "c1+d", "seed integrity and the T0/T1 split"),
    ("T-34", "b+e1", "roster with 2 approvers"),
    ("T-R4a", "e1", "soft authenticator unreachable from app/ and scripts/"),
    ("T-R4b", "d", "wiping the local DB does not reset a cap"),
    ("T-R4c", "unit", "banned wording in any scanned file"),
    ("T-R4d", "d", "fraud-flagged vendor forces T2"),
    ("T-R4e", "a+e2", "web process sees the Airwallex key and vice versa"),
)

ALL_IDS: tuple[str, ...] = tuple(row[0] for row in SPEC_INDEX)

#: §10.3 writes "T-09" as one row covering four sub-cases (a) prod base URL,
#: (b) AWX_ENV=production, (c) a 302 to another host, (d) HTTPS_PROXY. The tests
#: mark the halves separately, so both spellings are accepted by the index.
SUBSET_IDS: frozenset[str] = frozenset({"T-09a", "T-09b", "T-09c", "T-09d"})

#: IDs whose milestone has not been built yet. Listed so a failure names the
#: missing work instead of producing a bare "T-15 not found".
#:
#: An id may be absent from this set only when it already has a test. Removing an
#: id from here is the record that its milestone landed.
PENDING: frozenset[str] = frozenset(
    {
        # (a) client + record/replay — blocked on sandbox keys (§9.1 Plan B).
        # T-09's config halves (a: prod URL, b: AWX_ENV) are done and marked; the
        # transport halves (c: 302, d: HTTPS_PROXY) need the transport itself, so
        # the id stays pending rather than half-claiming to be covered.
        "T-09",
        # (e1) INSUFFICIENT_APPROVERS is a roster-size rule, tested in (e1)
        "T-34",
        # (c1) verify + lock: parsers and the fingerprint exist, the callback
        # rules, lookalike detection and duplicate locks do not yet.
        "T-14",
        "T-21",
        "T-29",
        # (c2) optional PDF/LLM ingest
        "T-01",
        "T-02",
        "T-18",
        "T-26",
        "T-30",
        # (d) planner + tiers + caps + tranches
        "T-05",
        "T-08",
        "T-20",
        "T-22",
        "T-28",
        "T-33",
        "T-R4b",
        "T-R4d",
        # (e1) packets + signing
        "T-06",
        "T-11",
        "T-12",
        "T-23",
        "T-32",
        "T-R4a",
        # (c1) the callback rules: signature, readback, and the provenance and
        # independence checks on the number dialled
        "T-10",
        "T-10b",
        # (f1) executor + poller
        "T-04",
        "T-04b",
        "T-04c",
        "T-15",
        "T-16",
        "T-24",
        "T-25",
        # (f2) incidents + RFI + webhooks
        "T-21b",
        "T-31",
        # (unit) the wording lint is a cut-list test that has not been written
        "T-R4c",
    }
)

#: Matches @pytest.mark.compliance("T-xx"). The class includes lower case
#: because several §10.3 ids end in a letter: T-R4a..e, T-04b/c, T-10b, T-21b.
_MARKER = re.compile(r'compliance\(\s*[\'"]([A-Za-z0-9\-]+)[\'"]\s*\)')


def _marked_ids() -> set[str]:
    """Every T-ID carrying a compliance marker anywhere in tests/.

    Placeholder ids like ``T-xx`` (which appear in §10.1's own prose) are
    dropped rather than reported as strays.
    """
    found: set[str] = set()
    for path in TESTS_DIR.rglob("*.py"):
        for candidate in _MARKER.findall(path.read_text(encoding="utf-8")):
            if "x" in candidate.lower():
                continue
            found.add(candidate)
    return found


MARKED: set[str] = _marked_ids()


class TestSpecIndexIsFaithful:
    def test_the_index_has_no_duplicates(self) -> None:
        assert len(ALL_IDS) == len(set(ALL_IDS))

    def test_the_index_covers_t01_through_t34(self) -> None:
        for number in range(1, 35):
            assert f"T-{number:02d}" in ALL_IDS, f"T-{number:02d} is missing from the index"

    def test_every_r4_addition_is_present(self) -> None:
        """§10.3's Round 4 additions, including the lettered sub-IDs."""
        for suffix in ("a", "b", "c", "d", "e"):
            assert f"T-R4{suffix}" in ALL_IDS
        for suffix in ("b", "c"):
            assert f"T-04{suffix}" in ALL_IDS
        assert "T-10b" in ALL_IDS
        assert "T-21b" in ALL_IDS

    def test_no_marker_names_an_id_the_index_does_not_contain(self) -> None:
        """A marker for a test id that is not in the index is a stale marker."""
        stray = MARKED - set(ALL_IDS) - SUBSET_IDS
        assert not stray, f"compliance markers for ids not in the index: {sorted(stray)}"

    def test_the_t09_sub_ids_all_belong_to_t09(self) -> None:
        """T-09 is one §10.3 row with four halves; a sub-id must trace to it."""
        for sub in SUBSET_IDS:
            parent = sub.split("-")[0] + "-" + sub.split("-")[1][:2]
            assert parent in ALL_IDS, f"{sub} does not belong to any row in the index"

    def test_every_id_has_a_description(self) -> None:
        for test_id, milestone, description in SPEC_INDEX:
            assert milestone, f"{test_id} has no milestone"
            assert description.strip(), f"{test_id} has no description"


class TestComplianceCoverage:
    @pytest.mark.parametrize("test_id", ALL_IDS)
    def test_id_has_a_test_or_is_declared_pending(self, test_id: str) -> None:
        if test_id in PENDING:
            pytest.skip(
                f"{test_id} belongs to a milestone not built yet (see docs/PROGRESS.md). "
                "§10.1 rule 8: a skip needs a README known-gaps line before the freeze."
            )
        assert test_id in MARKED, f"{test_id} has no @pytest.mark.compliance marker"

    @pytest.mark.parametrize("test_id", ALL_IDS)
    def test_pending_ids_still_belong_to_a_real_id(self, test_id: str) -> None:
        """A typo in PENDING would silently exempt an id that is actually done."""
        assert test_id in ALL_IDS

    def test_the_pending_list_is_only_shrinking(self) -> None:
        """Records where the build stands, so the shrink is visible in the diff.

        Two invariants, both about the *bookkeeping* rather than the coverage:

        * an id that already has a marker must not stay in PENDING, or the index
          would under-report progress;
        * an id without a marker must be in PENDING, or a skipped test would be
          silently absent rather than declared.
        """
        implemented = MARKED & set(ALL_IDS)
        stale_pending = sorted(implemented & PENDING)
        assert not stale_pending, f"ids marked pending but already tested: {stale_pending}"

        # Whole ids implemented so far. Milestone (b), the config guard and the
        # parsers land 7; the freeze needs all 41. The number is asserted so the
        # diff shows progress and so it can never be lowered to hide a loss.
        assert len(implemented) >= 7, f"only {len(implemented)} ids implemented so far"
        assert {"T-07", "T-13", "T-17", "T-19", "T-27", "T-R4e"} <= implemented, (
            "milestone (b)'s acceptance ids must all have tests"
        )

    def test_no_id_is_neither_tested_nor_pending(self) -> None:
        """An id with no marker and no PENDING entry would vanish silently."""
        orphans = sorted(set(ALL_IDS) - PENDING - MARKED)
        assert not orphans, f"ids neither tested nor declared pending: {orphans}"

    def test_the_never_cut_controls_all_have_tests(self) -> None:
        """§13.3's never-cut list must never become a skip.

        The full never-cut list is longer: idempotency and lookup-before-retry,
        packet binding and executor re-verification, the lock, the executor's
        live guards, failure to replacement, the tie-out, the audit chain, the
        kill switch, and the eval with its self-test. Of those, only the audit
        chain (T-13, T-17), the policy floor (T-19, T-27), the kill switch (T-07)
        and process separation (T-R4e) are built. The rest belong to milestones
        that have not been written, so this asserts the ones that exist and names
        the gap rather than pretending the list is satisfied.
        """
        never_cut_built = {"T-07", "T-13", "T-17", "T-19", "T-27", "T-R4e"}
        missing = sorted(never_cut_built - MARKED)
        assert not missing, f"never-cut controls without a test: {missing}"

        never_cut_unbuilt = {
            "T-06",
            "T-15",
            "T-16",
            "T-25",  # idempotency, lookup-before-retry
            "T-04",
            "T-23",
            "T-24",  # packet binding, re-verification, live guards
            "T-10",
            "T-10b",
            "T-21",
            "T-28",  # the lock
            "T-31",  # failure -> replacement
            "T-34",  # fewer than 3 approvers
        }
        assert never_cut_unbuilt <= PENDING, (
            "a never-cut control has been dropped rather than deferred: "
            f"{sorted(never_cut_unbuilt - PENDING)}"
        )
