"""Executable compliance registry with explicit removal of obsolete historical cases.

There is no deferred/not-written exemption. Every active case needs a marker on
an actual collected behavior test. Deletions and replacements are audited in
PROD-AUDIT.md and DECISIONS.md; deleted cases are not claimed as passing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SPEC_INDEX = (
    ("T-02", "c2", "memo claims a phone confirmation"),
    ("T-03", "c1+e2", "XSS name, SQL-ish invoice no, invalid reference"),
    ("T-04", "f1", "bank details change between sign-off and execution"),
    ("T-04b", "f1", "beneficiary last-4 differs (U16 fallback)"),
    ("T-04c", "f1", "first payment to new details: beneficiary created at execute"),
    ("T-06", "e1", "replayed approval assertion"),
    ("T-07", "b+f1", "HALT mid-run and unreadable HALT path"),
    ("T-08", "d", "daily caps and the IST day boundary"),
    ("T-09", "a", "prod URL, AWX_ENV, 302, HTTPS_PROXY"),
    ("T-10", "c1", "callback number taken from the change email"),
    ("T-10b", "c1+f1", "callback row without a valid ops signature"),
    ("T-11", "e1", "requester signs, same human twice, duplicate roster email"),
    ("T-12", "e1+f1", "quote expiring inside 120s, re-quote drift"),
    ("T-13", "b", "audit_log UPDATE and an offline edit"),
    ("T-15", "f1", "crash after transfers/create, before the DB write"),
    ("T-16", "f1", "AMBIGUOUS attempt then a re-plan in another run"),
    ("T-17", "b+f1", "audit DB unwritable"),
    ("T-19", "b", "policy lowers the floor unsigned; unknown key"),
    ("T-21b", "f2", "replayed webhook; FAILED webhook vs GET SENT"),
    ("T-23", "e1", "forged APPROVED status via SQL"),
    ("T-24", "f1", "balance drops below the floor between sign-off and execute"),
    ("T-25", "f1", "fx/conversions/create times out"),
    ("T-27", "b", "loosen any floor row, parametrised"),
    ("T-28", "c1+d+f1", "callback confirmed, then a capped first payment with tranches"),
    ("T-29", "c1", "phone edited day 0, IBAN change day 2"),
    ("T-31", "f2", "compliance failure_type trips and holds"),
    ("T-32", "e1", "MIN_1 quote is never bookable"),
    ("T-34", "b+e1", "roster with 2 approvers"),
    ("T-R4a", "e1", "soft authenticator unreachable from app/ and scripts/"),
    ("T-R4b", "d", "wiping the local DB does not reset a cap"),
    ("T-R4e", "a+e2", "web process sees the Airwallex key and vice versa"),
)

REMOVED = {
    "T-01": (
        "Deleted: optional PDF/OCR hidden-text extraction is absent. Evidence uploads are "
        "stored as attachments and never parsed into payment terms."
    ),
    "T-05": (
        "Deleted: the specified 3x1900 T0 automatic-payment scenario is incompatible with "
        "mandatory human approval. Active velocity and daily caps are tested under T-08 and "
        "T-R4b."
    ),
    "T-14": (
        "Deleted: bank-account ownership verification API is not integrated or claimed; "
        "beneficiary schema validation and signed manual review do not simulate "
        "FULL_MATCH/CANNOT_VERIFY."
    ),
    "T-18": (
        "Deleted: no LLM service is in the product path, so a fictional LLM outage is not "
        "an application test."
    ),
    "T-20": (
        "Deleted: multi-item shared FX funding is unsupported; each conversion binds to one "
        "human-approved payment. Actual quote/amount binding remains tested."
    ),
    "T-21": (
        "Deleted: PDF onboarding extraction does not exist. Manual bank changes cannot "
        "supply their own callback phone; that real boundary is tested under T-10."
    ),
    "T-22": (
        "Deleted: sub-dollar history enabling T0 applies to removed automatic approval. "
        "Current payments require humans regardless of history."
    ),
    "T-26": (
        "Deleted: instructions in a document are never executed against other invoices; "
        "optional document extraction is absent."
    ),
    "T-30": (
        "Deleted: no LLM-extracted bank identifier competes with the parser in the "
        "supported manual intake path."
    ),
    "T-33": (
        "Deleted: runtime seeding and automatic T0/T1 split were removed. Archive isolation "
        "is tested under T-R4a; actual signed caps/tranches under T-28."
    ),
    "T-R4c": (
        "Deleted: recording-caption vocabulary freeze is not application behavior. Root "
        "demo files remain untouched; product-source dispositions are recorded in this "
        "audit."
    ),
    "T-R4d": (
        "Deleted: the weaker allow-fraud-with-T2 expectation does not apply. Flagged "
        "obligations are blocked outright by build_payment, including for two approvers."
    ),
}


def marked_tests():
    result = {}

    def visit(path, item, inherited=()):
        marks = list(inherited)
        for decorator in getattr(item, "decorator_list", ()):
            if (
                isinstance(decorator, ast.Call)
                and ast.unparse(decorator.func) == "pytest.mark.compliance"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
            ):
                marks.append(decorator.args[0].value)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if item.name.startswith("test_"):
                for marker in marks:
                    result.setdefault(marker, []).append((path, item.name))
            return
        for child in getattr(item, "body", ()):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(path, child, marks)

    for path in Path(__file__).resolve().parents[1].rglob("test_*.py"):
        visit(path, ast.parse(path.read_text(encoding="utf-8")))
    return result


@pytest.mark.parametrize("test_id", [row[0] for row in SPEC_INDEX])
def test_active_case_has_a_collected_behavior_test(test_id, request):
    marked = marked_tests().get(test_id, [])
    assert marked, f"No behavior test for {test_id}"
    collected = {
        (Path(item.path).resolve(), item.originalname)
        for item in request.session.items
        if hasattr(item, "originalname")
    }
    assert any((p.resolve(), name) in collected for p, name in marked), test_id


def test_registry_has_no_silent_or_deferred_cases():
    ids = [row[0] for row in SPEC_INDEX]
    assert len(ids) == len(set(ids))
    historical = {f"T-{number:02d}" for number in range(1, 35)}
    historical |= {"T-04b", "T-04c", "T-10b", "T-21b"}
    historical |= {f"T-R4{suffix}" for suffix in "abcde"}
    assert set(ids) | REMOVED.keys() == historical
    assert all(milestone and description.strip() for _, milestone, description in SPEC_INDEX)
    assert not set(ids) & REMOVED.keys()
    marked = marked_tests()
    assert not set(marked) - set(ids) - {"T-09a", "T-09b", "T-09c", "T-09d"}
    assert all(why.startswith("Deleted:") for why in REMOVED.values())
    for path in Path(__file__).parent.rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "skip"
            for n in ast.walk(tree)
        ), path
