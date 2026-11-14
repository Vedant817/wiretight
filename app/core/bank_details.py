"""Typed bank destinations and encrypted, immutable identifier versions."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal, Self
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import audit, db, parsers
from app.core.operators import utcnow


class BankDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    company_name: str = Field(min_length=1, max_length=200)
    country: Literal["US", "GB", "DE", "NL", "FR"]
    currency: Literal["USD", "GBP", "EUR"]
    method: Literal["LOCAL", "SWIFT"] = "LOCAL"
    account_name: str = Field(min_length=1, max_length=200)
    account_number: str = Field(default="", max_length=34)
    iban: str = Field(default="", max_length=34)
    routing_value: str = Field(default="", max_length=9)
    bank_name: str = Field(default="", max_length=200)
    swift_code: str = Field(default="", max_length=11)
    bank_account_category: Literal["Checking", "Savings"] | None = None

    @model_validator(mode="after")
    def valid_corridor(self) -> Self:
        if self.country == "US" and self.bank_account_category is None:
            raise ValueError("Select the actual US bank account category")
        if (self.country, self.currency) not in {
            ("US", "USD"),
            ("GB", "GBP"),
            ("DE", "EUR"),
            ("NL", "EUR"),
            ("FR", "EUR"),
        }:
            raise ValueError("Unsupported country/currency corridor")
        if self.country in {"DE", "NL", "FR"}:
            result = parsers.parse_iban(self.iban)
            if (
                not result.valid
                or result.country != self.country
                or self.account_number
                or self.routing_value
            ):
                raise ValueError("Provide only a valid IBAN matching the bank country")
        else:
            if self.iban or not re.fullmatch(r"[0-9]{4,34}", self.account_number):
                raise ValueError("Provide a numeric bank account number")
            routing = (
                parsers.parse_aba(self.routing_value)
                if self.country == "US"
                else parsers.parse_sort_code(self.routing_value)
            )
            if not routing.valid or not any(digit in "123456789" for digit in self.routing_value):
                raise ValueError("Invalid bank routing identifier")
            if self.country == "GB" and not self.bank_name:
                raise ValueError("GB bank name is required")
        if self.method == "SWIFT" and not parsers.parse_bic(self.swift_code).valid:
            raise ValueError("SWIFT requires a valid BIC")
        return self

    def fingerprint(self) -> str:
        return parsers.fingerprint(
            parsers.PayeeDetails(
                country=self.country,
                currency=self.currency,
                method=self.method,
                account=self.iban or self.account_number,
                bic=self.swift_code or None,
                extra={"routing": re.sub(r"[^0-9]", "", self.routing_value)}
                if self.routing_value
                else {},
            )
        )

    def rail(self) -> Literal["SWIFT", "ACH", "FPS", "SEPA"]:
        if self.method == "SWIFT":
            return "SWIFT"
        if self.country == "US":
            return "ACH"
        if self.country == "GB":
            return "FPS"
        return "SEPA"

    def beneficiary_payload(self, nickname: str) -> dict[str, Any]:
        bank: dict[str, str] = {
            "bank_country_code": self.country,
            "account_currency": self.currency,
            "account_name": self.account_name,
        }
        if self.iban:
            bank["iban"] = self.iban.replace(" ", "").upper()
        else:
            bank.update(
                account_number=self.account_number,
                account_routing_type1="aba" if self.country == "US" else "sort_code",
                account_routing_value1=re.sub(r"[^0-9]", "", self.routing_value),
            )
        if self.country == "US" and self.bank_account_category is not None:
            bank["bank_account_category"] = self.bank_account_category
        if self.bank_name:
            bank["bank_name"] = self.bank_name
        if self.swift_code:
            bank["swift_code"] = self.swift_code
        if self.method == "LOCAL":
            bank["local_clearing_system"] = self.rail()
        return {
            "nickname": nickname,
            "transfer_methods": [self.method],
            "beneficiary": {
                "entity_type": "COMPANY",
                "company_name": self.company_name,
                "bank_details": bank,
            },
        }

    def matches_provider(self, value: dict[str, Any]) -> bool:
        entity = value.get("beneficiary", value)
        if isinstance(entity, str):
            try:
                entity = json.loads(entity)
            except ValueError:
                return False
        if not isinstance(entity, dict):
            return False
        entity = entity.get("bank_transfer_beneficiary", entity)
        bank = entity.get("bank_details", {}) if isinstance(entity, dict) else {}
        if not isinstance(bank, dict):
            return False
        expected = self.beneficiary_payload("")["beneficiary"]["bank_details"]
        # Full destination identifiers are mandatory. Last-four-only responses
        # are insufficient authority to pay; no guessed fingerprint fallback.
        for key in (
            "bank_country_code",
            "account_currency",
            "account_name",
            "iban" if self.iban else "account_number",
        ):
            if (
                key not in bank
                or re.sub(r"\s", "", str(bank[key])).upper()
                != re.sub(r"\s", "", expected[key]).upper()
            ):
                return False
        if not self.iban:
            if bank.get("account_routing_type1") != expected["account_routing_type1"]:
                return False
            if (
                re.sub(r"[^0-9]", "", str(bank.get("account_routing_value1", "")))
                != expected["account_routing_value1"]
            ):
                return False
        if self.country == "US" and bank.get("bank_account_category") != self.bank_account_category:
            return False
        return not (self.method == "SWIFT" and bank.get("swift_code") != self.swift_code)


class DetailVault:
    def __init__(self, key_path: str | Path) -> None:
        self._cipher = Fernet(Path(key_path).read_bytes().strip())

    def encrypt_json(self, value: dict[str, Any]) -> str:
        return self._cipher.encrypt(audit.canonical_json(value).encode()).decode()

    def encrypt_bytes(self, value: bytes) -> bytes:
        return self._cipher.encrypt(value)

    def decrypt_bytes(self, value: bytes) -> bytes:
        return self._cipher.decrypt(value)

    def decrypt_json(self, value: str) -> dict[str, Any]:
        decoded: dict[str, Any] = json.loads(self._cipher.decrypt(value.encode()))
        return decoded

    def store(self, conn: db.Connection, details: BankDetails) -> str:
        identifier = str(uuid4())
        raw = audit.canonical_json(details.model_dump()).encode()
        with db.transaction(conn):
            conn.execute(
                "INSERT INTO "
                "protected_details(id,encrypted_json,sha256,created_at) "
                "VALUES(?,?,?,?)",
                (
                    identifier,
                    self._cipher.encrypt(raw),
                    hashlib.sha256(raw).hexdigest(),
                    utcnow().isoformat(),
                ),
            )
        return identifier

    def load(self, conn: db.Connection, identifier: str) -> BankDetails:
        row = conn.execute(
            "SELECT encrypted_json,sha256 FROM protected_details WHERE id=?", (identifier,)
        ).fetchone()
        if not row:
            raise ValueError("Bank-detail version is missing")
        try:
            raw = self._cipher.decrypt(row["encrypted_json"])
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Bank-detail version integrity check failed")
            return BankDetails.model_validate(json.loads(raw))
        except (InvalidToken, ValueError):
            raise ValueError("Bank-detail version cannot be authenticated") from None
