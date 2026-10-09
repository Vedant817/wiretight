"""The policy floor: 30 hard-coded rows that a policy file may only tighten.

FINAL.md §4.15, §10.3 T-19 and T-27.

This is the part of Wiretight where "fail closed" is literal. A policy file is
not configuration; it is a request to be *allowed* to do something, and the
floor decides whether the request is within bounds. Loosening any row, adding an
unknown key, or presenting a policy without two distinct approver signatures is a
load error, which trips the kill switch and exits non-zero.

T-27 requires a test per row, parametrised over all 30. That is the mechanism
that stops a row from being added to the floor without a corresponding attempt
to loosen it.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core import db
from app.core.policy import (
    LoadedPolicy,
    PolicyError,
    load_policy,
    sign_policy_bytes,
)
from app.core.policy_floor import (
    FLOOR_ROWS,
    Direction,
    FloorRow,
    check_policy_against_floor,
)

#: The shipped default, exactly as §4.17 writes it. T-27 mutates a copy of this.
BASE_POLICY: dict[str, Any] = {
    "policy_version": "2026-11-01.1",
    "entity_id": "halden-robotics-demo",
    "base_currency": "USD",
    "reserve_floor": {"USD": "8000.00"},
    "roster": [
        {
            "id": "arun",
            "name": "Arun (AP clerk)",
            "role": "approver",
            "email": "arun@halden.example",
        },
        {
            "id": "meera",
            "name": "Meera (finance lead)",
            "role": "approver",
            "email": "meera@halden.example",
        },
        {
            "id": "kabir",
            "name": "Kabir (founder)",
            "role": "approver",
            "email": "kabir@halden.example",
        },
        {"id": "priya", "name": "Priya (ops)", "role": "ops", "email": "priya@halden.example"},
    ],
    "bank_change": {
        "cooling_off_hours": 72,
        "callback_contact_min_age_days": 30,
        "callback_validity_days": 7,
        "contact_provenance_min_invoice_age_days": 90,
        "first_payment_cap_usd": "2500.00",
        "first_payment_cap_median_fraction": "0.50",
        "cap_lift_final_payments": 2,
    },
    "t0": {
        "enabled": False,
        "per_payment_limit_usd": "2000.00",
        "min_final_payments": 3,
        "min_payment_fraction_of_limit": "0.25",
        "bank_details_unchanged_days": 60,
        "max_multiple_of_payee_median": "1.5",
        "disqualifiers": [
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
    },
    "tiers": {
        "t2_threshold_usd": "10000.00",
        "t2_payee_7d_aggregate_usd": "10000.00",
    },
    "limits": {
        "per_run": {"t0_usd": "6000.00", "all_usd": "50000.00", "max_payments": 40},
        "per_day": {
            "t0_usd": "6000.00",
            "all_usd": "75000.00",
            "max_payments": 60,
            "max_runs": 2,
            "max_new_beneficiaries": 5,
            "calendar_tz": "Asia/Kolkata",
        },
        "per_payee_7d": {"t0_usd": "2000.00"},
        "per_payee_24h": {"max_t0": 1, "max_payments": 3},
        "per_approver_day_usd": "30000.00",
    },
    "approvals": {"max_validity_hours": 4, "challenge_ttl_seconds": 300},
    "fx": {"quote_validity": "HR_4", "quote_safety_margin_seconds": 120, "drift_bp": 25},
    "settlement": {
        "SEPA": {"business_days": 3, "calendar": "EUR_TARGET2", "min_hours": 48},
        "FPS": {"business_days": 3, "calendar": "GBP_ENGLAND", "min_hours": 48},
        "ACH": {"business_days": 2, "calendar": "USD_FED", "min_hours": 48},
        "SWIFT": {"final_by_timer": False, "presumed_settled_business_days": 10},
    },
    "ambiguous": {"escalate_after_days": 6},
    "killswitch": {
        "clock_skew_seconds": 120,
        "ambiguous_creates_per_run": 2,
        "ambiguous_creates_rolling_24h": 2,
        "failed_transfers_rolling_1h": 3,
        "extraction_conflicts_rolling_24h": 3,
        "clear_signatures": 2,
    },
    "rails": {
        "flight_business_days": {"SEPA": 2, "FPS": 1, "ACH": 2, "SWIFT": 3},
        "cutoff_local_time": {"SEPA": "14:00", "FPS": "14:00", "ACH": "14:00", "SWIFT": "12:00"},
        "fee_reservation_usd": {"SEPA": "5.00", "FPS": "5.00", "ACH": "5.00", "SWIFT": "30.00"},
    },
    "vendor_category_reason": {
        "freight": "freight",
        "manufacturing": "goods_purchased",
        "design_services": "professional_business_services",
        "software": "technical_services",
        "contractor": "professional_business_services",
    },
    "demo_timing": False,
}


@pytest.fixture()
def policy_copy() -> dict[str, Any]:
    return copy.deepcopy(BASE_POLICY)


def write_policy(path: Path, policy: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return path


def signed(tmp_path: Path, policy: dict[str, Any]) -> Path:
    """Write a policy with two valid, distinct approver signatures (floor row 30)."""
    import json

    path = write_policy(tmp_path / "policy.yaml", policy)
    signature = sign_policy_bytes(path.read_bytes(), ["meera", "kabir"])
    (tmp_path / "policy.sig.json").write_text(json.dumps(signature), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The floor table itself
# ---------------------------------------------------------------------------
class TestFloorTable:
    def test_there_are_exactly_thirty_rows(self) -> None:
        """§4.15 lists 30 rows. A 31st needs a row here and a test to match."""
        assert len(FLOOR_ROWS) == 30

    def test_row_numbers_are_one_through_thirty(self) -> None:
        assert sorted(row.number for row in FLOOR_ROWS) == list(range(1, 31))

    def test_every_row_names_the_section_it_comes_from(self) -> None:
        for row in FLOOR_ROWS:
            assert row.source, f"row {row.number} does not cite a FINAL.md section"

    def test_every_row_declares_a_direction(self) -> None:
        for row in FLOOR_ROWS:
            assert row.direction in {Direction.MINIMUM, Direction.MAXIMUM, Direction.SUPERSET}


# ---------------------------------------------------------------------------
# T-27: parametrised over all 30 rows. This is what makes a new row mandatory.
# ---------------------------------------------------------------------------
def _loosen(row: FloorRow, policy: dict[str, Any]) -> None:
    """Apply a deliberate violation of ``row`` to ``policy``, in place."""
    if row.number == 1:
        policy["bank_change"]["cooling_off_hours"] = 1
    elif row.number == 2:
        policy["bank_change"]["callback_contact_min_age_days"] = 0
    elif row.number == 3:
        policy["bank_change"]["callback_validity_days"] = 90
        policy["bank_change"]["contact_provenance_min_invoice_age_days"] = 1
    elif row.number == 4:
        policy["bank_change"]["first_payment_cap_usd"] = "999999.00"
    elif row.number == 5:
        policy["bank_change"]["cap_lift_final_payments"] = 1
    elif row.number == 6:
        policy["t0"]["per_payment_limit_usd"] = "5000.00"
    elif row.number == 7:
        policy["t0"]["min_final_payments"] = 1
        policy["t0"]["min_payment_fraction_of_limit"] = "0.01"
        policy["t0"]["bank_details_unchanged_days"] = 1
    elif row.number == 8:
        policy["t0"]["max_multiple_of_payee_median"] = "99.0"
    elif row.number == 9:
        policy["t0"]["disqualifiers"] = []
    elif row.number == 10:
        # A string that YAML reads as truthy. T0 must be a real boolean, and the
        # floor check is what refuses this: `if str(policy["t0"]["enabled"])` would
        # happily enable auto-pay from the string "no".
        policy["t0"]["enabled"] = "false-but-written-as-a-string"
    elif row.number == 11:
        policy["tiers"]["t2_threshold_usd"] = "0.01"
    elif row.number == 12:
        policy["tiers"]["t2_payee_7d_aggregate_usd"] = "0.01"
    elif row.number == 13:
        policy["limits"]["per_run"]["t0_usd"] = "999999.00"
        policy["limits"]["per_run"]["all_usd"] = "999999.00"
        policy["limits"]["per_run"]["max_payments"] = 500
    elif row.number == 14:
        policy["limits"]["per_day"]["all_usd"] = "999999.00"
        policy["limits"]["per_day"]["max_payments"] = 500
        policy["limits"]["per_day"]["max_runs"] = 99
        policy["limits"]["per_day"]["max_new_beneficiaries"] = 500
    elif row.number == 15:
        policy["limits"]["per_payee_7d"]["t0_usd"] = "999999.00"
    elif row.number == 16:
        policy["limits"]["per_payee_24h"] = {"max_t0": 50, "max_payments": 500}
    elif row.number == 17:
        policy["limits"]["per_approver_day_usd"] = "999999.00"
    elif row.number == 18:
        policy["approvals"] = {"max_validity_hours": 72, "challenge_ttl_seconds": 86400}
    elif row.number == 19:
        policy["fx"]["quote_safety_margin_seconds"] = 0
    elif row.number == 20:
        policy["fx"]["drift_bp"] = 5000
    elif row.number == 21:
        policy["reserve_floor"] = {}  # missing: the executor must refuse to start
    elif row.number == 22:
        policy["settlement"]["SEPA"]["min_hours"] = 0
        policy["settlement"]["SEPA"]["business_days"] = 0
        policy["settlement"]["FPS"]["business_days"] = 0
        policy["settlement"]["ACH"]["business_days"] = 0
        policy["settlement"]["SWIFT"]["final_by_timer"] = True
        policy["settlement"]["SWIFT"]["presumed_settled_business_days"] = 0
    elif row.number == 23:
        policy["ambiguous"]["escalate_after_days"] = 0
    elif row.number == 24:
        policy["killswitch"]["clock_skew_seconds"] = 100000
    elif row.number == 25:
        policy["rails"]["fee_reservation_usd"]["SEPA"] = "0.00"
    elif row.number == 26:
        policy["killswitch"]["ambiguous_creates_per_run"] = 500
        policy["killswitch"]["ambiguous_creates_rolling_24h"] = 500
    elif row.number == 27:
        policy["killswitch"]["failed_transfers_rolling_1h"] = 500
    elif row.number == 28:
        policy["killswitch"]["extraction_conflicts_rolling_24h"] = 500
    elif row.number == 29:
        policy["rails"]["flight_business_days"]["SEPA"] = 0  # never shorten a rail window
    elif row.number == 30:
        policy["killswitch"]["clear_signatures"] = 1
    else:  # pragma: no cover - guarded by test_there_are_exactly_thirty_rows
        raise AssertionError(f"row {row.number} has no loosen case")


@pytest.mark.compliance("T-27")
@pytest.mark.parametrize("row_number", sorted(row.number for row in FLOOR_ROWS))
def test_t27_every_floor_row_has_a_loosen_test(
    row_number: int, policy_copy: dict[str, Any], tmp_path: Path
) -> None:
    """T-27: "parametrised over all 30 rows; a row without a test fails".

    Each row is violated on purpose and the loader must refuse it, naming the
    row. If this test cannot find a row to violate, that is the failure.
    """
    row = next(r for r in FLOOR_ROWS if r.number == row_number)
    _loosen(row, policy_copy)
    path = write_policy(tmp_path / "policy.yaml", policy_copy)

    with pytest.raises(PolicyError) as caught:
        load_policy(path, signature_path=None, allow_unsigned=True)

    assert f"r{row_number}" in str(caught.value) or row.control in str(caught.value), (
        f"row {row_number} was refused, but not by name: {caught.value}"
    )


# ---------------------------------------------------------------------------
# The shipped policy must itself be valid
# ---------------------------------------------------------------------------
class TestShippedPolicyIsValid:
    def test_the_example_policy_passes_the_floor(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        result = check_policy_against_floor(policy_copy)
        assert result.ok, result.violations
        assert path.exists()

    def test_the_demo_policy_passes_the_floor(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["t0"]["enabled"] = True
        policy_copy["demo_timing"] = True
        assert check_policy_against_floor(policy_copy).ok

    def test_the_roster_is_the_d6_cast(self, policy_copy: dict[str, Any]) -> None:
        roster = policy_copy["roster"]
        assert [entry["id"] for entry in roster] == ["arun", "meera", "kabir", "priya"]
        assert sum(1 for entry in roster if entry["role"] == "approver") == 3
        assert sum(1 for entry in roster if entry["role"] == "ops") == 1

    def test_ops_never_appears_in_the_approver_count(self, policy_copy: dict[str, Any]) -> None:
        """Priya records callbacks and can never sign."""
        assert policy_copy["roster"][3]["role"] == "ops"


# ---------------------------------------------------------------------------
# Tightening is allowed. Loosening is not.
# ---------------------------------------------------------------------------
class TestTighteningIsAllowed:
    def test_a_higher_t2_threshold_is_accepted(self, policy_copy: dict[str, Any]) -> None:
        """Raising the T1/T2 boundary sends more items to two sign-offs: stricter.

        Lowering it to 5,000 would let a 9,000 payment through on one signature,
        so that is the loosening T-27 row 11 refuses.
        """
        policy_copy["tiers"]["t2_threshold_usd"] = "25000.00"
        assert check_policy_against_floor(policy_copy).ok

    def test_a_lower_t2_threshold_is_refused(self, policy_copy: dict[str, Any]) -> None:
        policy_copy["tiers"]["t2_threshold_usd"] = "5000.00"
        result = check_policy_against_floor(policy_copy)
        assert not result.ok
        assert any("r11" in violation for violation in result.violations)

    def test_a_longer_cooling_off_is_accepted(self, policy_copy: dict[str, Any]) -> None:
        policy_copy["bank_change"]["cooling_off_hours"] = 168
        assert check_policy_against_floor(policy_copy).ok

    def test_a_lower_first_payment_cap_is_accepted(self, policy_copy: dict[str, Any]) -> None:
        policy_copy["bank_change"]["first_payment_cap_usd"] = "500.00"
        assert check_policy_against_floor(policy_copy).ok

    def test_a_larger_disqualifier_list_is_accepted(self, policy_copy: dict[str, Any]) -> None:
        policy_copy["t0"]["disqualifiers"] = [*policy_copy["t0"]["disqualifiers"], "brand_new_flag"]
        assert check_policy_against_floor(policy_copy).ok

    def test_a_higher_reserve_floor_is_accepted(self, policy_copy: dict[str, Any]) -> None:
        policy_copy["reserve_floor"] = {"USD": "20000.00"}
        assert check_policy_against_floor(policy_copy).ok

    def test_t0_off_is_accepted_and_is_the_default(self, policy_copy: dict[str, Any]) -> None:
        assert policy_copy["t0"]["enabled"] is False
        assert check_policy_against_floor(policy_copy).ok


# ---------------------------------------------------------------------------
# Unknown keys, tags, anchors, types
# ---------------------------------------------------------------------------
class TestUnknownAndHostileYaml:
    def test_an_unknown_top_level_key_is_a_load_error(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["duplicates"] = {"enabled": False}
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="unknown"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_the_skip_callback_key_is_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        """§4.15 names this one explicitly."""
        policy_copy["bank_change"]["skip_callback"] = True
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="unknown"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_an_unknown_nested_key_is_a_load_error(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["t0"]["trust_the_model"] = True
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="unknown"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_yaml_tag_is_refused(self, tmp_path: Path, policy_copy: dict[str, Any]) -> None:
        path = tmp_path / "policy.yaml"
        body = yaml.safe_dump(policy_copy, sort_keys=False)
        path.write_text(
            body + "\nx: !!python/object/apply:os.system ['echo hi']\n", encoding="utf-8"
        )
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_yaml_anchor_is_refused(self, tmp_path: Path, policy_copy: dict[str, Any]) -> None:
        """An anchor can be used to smuggle in a merge the floor never saw."""
        path = tmp_path / "policy.yaml"
        path.write_text(
            "base: &b\n  t2_threshold_usd: '0.01'\npolicy_version: 'x'\n<<: *b\n",
            encoding="utf-8",
        )
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_missing_required_key_is_a_load_error(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        del policy_copy["bank_change"]["cooling_off_hours"]
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="missing"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_missing_reserve_floor_is_a_load_error(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        del policy_copy["reserve_floor"]
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="r21"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_duplicate_roster_email_is_a_load_error(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["roster"][2]["email"] = policy_copy["roster"][1]["email"]
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match="email"):
            load_policy(path, signature_path=None, allow_unsigned=True)


# ---------------------------------------------------------------------------
# T-19: signatures
# ---------------------------------------------------------------------------
@pytest.mark.compliance("T-19")
class TestPolicySignatures:
    def test_a_policy_that_lowers_the_floor_and_is_unsigned_is_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        """T-19: the signature is what makes a change to the floor legitimate."""
        policy_copy["tiers"]["t2_threshold_usd"] = "0.01"
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=False)

    def test_one_signature_is_not_enough(self, tmp_path: Path, policy_copy: dict[str, Any]) -> None:
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        import json

        sig = tmp_path / "policy.sig.json"
        sig.write_text(
            json.dumps(sign_policy_bytes(path.read_bytes(), ["meera"])),
            encoding="utf-8",
        )
        with pytest.raises(PolicyError, match=r"2|two|signature"):
            load_policy(path, signature_path=sig, allow_unsigned=False)

    def test_two_signatures_from_the_same_approver_are_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        import json

        sig = tmp_path / "policy.sig.json"
        sig.write_text(
            json.dumps(sign_policy_bytes(path.read_bytes(), ["meera", "meera"])),
            encoding="utf-8",
        )
        with pytest.raises(PolicyError, match="distinct"):
            load_policy(path, signature_path=sig, allow_unsigned=False)

    def test_two_distinct_signatures_load(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        path = signed(tmp_path, policy_copy)
        loaded = load_policy(
            path, signature_path=tmp_path / "policy.sig.json", allow_unsigned=False
        )
        assert isinstance(loaded, LoadedPolicy)
        assert loaded.sha256

    def test_a_signature_over_different_bytes_does_not_verify(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        path = signed(tmp_path, policy_copy)
        import json

        other = copy.deepcopy(policy_copy)
        other["tiers"]["t2_threshold_usd"] = "5000.00"
        write_policy(tmp_path / "policy.yaml", other)

        json.loads((tmp_path / "policy.sig.json").read_text(encoding="utf-8"))
        with pytest.raises(PolicyError, match=r"sha256|signature|digest"):
            load_policy(path, signature_path=tmp_path / "policy.sig.json", allow_unsigned=False)

    def test_the_load_is_recorded_in_policy_load(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        conn = db.connect(tmp_path / "app.sqlite")
        try:
            path = signed(tmp_path, policy_copy)
            load_policy(
                path, signature_path=tmp_path / "policy.sig.json", allow_unsigned=False, conn=conn
            )
            rows = list(conn.execute("SELECT path, sha256, result FROM policy_load"))
            assert len(rows) == 1
            assert rows[0]["result"] == "OK"
            assert len(rows[0]["sha256"]) == 64
        finally:
            conn.close()

    def test_a_rejected_load_is_recorded_too(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        conn = db.connect(tmp_path / "app.sqlite")
        try:
            policy_copy["duplicates"] = {"enabled": False}
            path = write_policy(tmp_path / "policy.yaml", policy_copy)
            with pytest.raises(PolicyError):
                load_policy(path, signature_path=None, allow_unsigned=True, conn=conn)
            rows = list(conn.execute("SELECT result FROM policy_load"))
            assert [row["result"] for row in rows] == ["REJECTED"]
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# The value type matters as much as the bound
# ---------------------------------------------------------------------------
class TestValueTypes:
    def test_a_money_value_must_be_a_string_not_a_number(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        """A YAML float is a float, and a float is not a signed amount."""
        policy_copy["bank_change"]["first_payment_cap_usd"] = 2500.00
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError, match=r"float|string"):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_boolean_where_a_number_belongs_is_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["bank_change"]["cooling_off_hours"] = True
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_a_negative_money_value_is_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["reserve_floor"] = {"USD": "-1.00"}
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=True)

    def test_an_out_of_range_bp_is_refused(
        self, tmp_path: Path, policy_copy: dict[str, Any]
    ) -> None:
        policy_copy["fx"]["drift_bp"] = -5
        path = write_policy(tmp_path / "policy.yaml", policy_copy)
        with pytest.raises(PolicyError):
            load_policy(path, signature_path=None, allow_unsigned=True)


# ---------------------------------------------------------------------------
# Floor row 21: a missing reserve floor must stop the executor starting
# ---------------------------------------------------------------------------
@pytest.mark.compliance("T-19")
def test_row21_a_missing_reserve_floor_names_the_row(
    tmp_path: Path, policy_copy: dict[str, Any]
) -> None:
    policy_copy["reserve_floor"] = {}
    path = write_policy(tmp_path / "policy.yaml", policy_copy)
    with pytest.raises(PolicyError, match="r21"):
        load_policy(path, signature_path=None, allow_unsigned=True)


# ---------------------------------------------------------------------------
# Floor row 10: T0 needs two signatures to be turned on
# ---------------------------------------------------------------------------
def test_t0_enabled_with_two_signatures_loads(tmp_path: Path, policy_copy: dict[str, Any]) -> None:
    """policy.demo.yaml turns T0 on, signed, and labelled. That is allowed."""
    policy_copy["t0"]["enabled"] = True
    policy_copy["demo_timing"] = True
    path = signed(tmp_path, policy_copy)
    loaded = load_policy(path, signature_path=tmp_path / "policy.sig.json", allow_unsigned=False)
    assert loaded.policy["t0"]["enabled"] is True
    assert loaded.policy["demo_timing"] is True


def test_t0_enabled_is_refused_as_a_bare_bool(tmp_path: Path, policy_copy: dict[str, Any]) -> None:
    policy_copy["t0"]["enabled"] = "true"
    path = write_policy(tmp_path / "policy.yaml", policy_copy)
    with pytest.raises(PolicyError, match=r"bool|boolean"):
        load_policy(path, signature_path=None, allow_unsigned=True)


def test_demo_timing_without_the_flag_pair_is_refused(
    tmp_path: Path, policy_copy: dict[str, Any]
) -> None:
    """demo_timing shortens cooling-off, so it may not appear without t0 off+on context."""
    policy_copy["demo_timing"] = "yes"
    path = write_policy(tmp_path / "policy.yaml", policy_copy)
    with pytest.raises(PolicyError, match=r"bool|boolean"):
        load_policy(path, signature_path=None, allow_unsigned=True)


# ---------------------------------------------------------------------------
# Nothing here may reach the network or the model
# ---------------------------------------------------------------------------
def test_the_floor_module_does_not_import_the_llm() -> None:
    from pathlib import Path as _Path

    source = (_Path(__file__).resolve().parents[2] / "app" / "core" / "policy_floor.py").read_text(
        encoding="utf-8"
    )
    assert "import anthropic" not in source
    assert "openai" not in source


@pytest.fixture(autouse=True)
def _no_side_effects() -> Iterator[None]:
    yield
    # A failed load must never leave a half-written policy file behind.
    assert not list(Path("var").glob("policy*.yaml")) if Path("var").exists() else True
