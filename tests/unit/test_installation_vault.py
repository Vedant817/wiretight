# ruff: noqa: F811

import pytest

from app.core import installation, runtime_policy
from app.core.bank_details import BankDetails, DetailVault
from tests.unit.test_operators_signing import domain  # noqa: F401


def test_installation_uses_supplied_business_and_never_overwrites_policy(domain, tmp_path):
    database, _ = domain
    conn = database.connection()
    path = tmp_path / "policy.yaml"
    installation.initialize(
        conn,
        legal_name="Fixture real-input business",
        reserve_usd="12345.67",
        policy_path=path,
        key_dir=tmp_path / "keys",
        seal_dir=tmp_path / "seals",
    )
    loaded, _ = runtime_policy.validated_policy(conn, path)
    assert loaded.policy["reserve_floor"]["USD"] == "12345.67"
    assert (
        conn.execute("SELECT legal_name FROM entity").fetchone()[0] == "Fixture real-input business"
    )
    assert (
        conn.execute("SELECT COUNT(*) FROM vendor").fetchone()[0] == 1
    )  # pre-existing fixture only
    with pytest.raises(ValueError, match="overwrite"):
        installation.initialize(
            conn,
            legal_name="Different input",
            reserve_usd="10.00",
            policy_path=path,
            key_dir=tmp_path / "keys",
            seal_dir=tmp_path / "seals",
        )


def test_vault_round_trip_is_encrypted_and_authentication_failure_is_closed(domain, tmp_path):
    from cryptography.fernet import Fernet

    database, _ = domain
    conn = database.connection()
    path = tmp_path / "details.key"
    path.write_bytes(Fernet.generate_key())
    vault = DetailVault(path)
    bank = BankDetails(
        company_name="Fixture supplier",
        country="US",
        currency="USD",
        account_name="Fixture account",
        account_number="123456789",
        routing_value="021000021",
    )
    identifier = vault.store(conn, bank)
    raw = conn.execute(
        "SELECT encrypted_json FROM protected_details WHERE id=?", (identifier,)
    ).fetchone()[0]
    assert b"123456789" not in raw and b"Fixture account" not in raw
    assert vault.load(conn, identifier) == bank
    path.write_bytes(Fernet.generate_key())
    with pytest.raises(ValueError, match="authenticated"):
        DetailVault(path).load(conn, identifier)


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "EUR"},
        {"routing_value": "000000000"},
        {"country": "ZZ"},
        {"account_number": "1.0"},
    ],
)
def test_unsupported_or_malformed_bank_destination_refused(changes):
    with pytest.raises(ValueError):
        BankDetails.model_validate(
            {
                "company_name": "Fixture supplier",
                "country": "US",
                "currency": "USD",
                "account_name": "Fixture account",
                "account_number": "123456789",
                "routing_value": "021000021",
                **changes,
            }
        )
