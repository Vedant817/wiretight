"""Human-approved durable payout execution. This is the only wallet mutation caller.

An intent and approval consumption commit before any POST. Existing PREPARED or
AMBIGUOUS intents are lookup-only on restart; a process cannot infer that a missing
response meant a missing payout. No simulator, fixture loader, or test signer.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from sqlite3 import Row
from typing import Any
from uuid import UUID, uuid4, uuid5
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core import audit, db, killswitch, packets, signing, trust
from app.core.bank_details import BankDetails, DetailVault
from app.core.operators import utcnow
from app.core.policy import LoadedPolicy, PolicyError
from app.core.process_lock import exclusive_process
from app.core.runtime_policy import load_runtime_policy
from app.integrations.airwallex import AirwallexClient, ProviderError, Transfer, TransferRequest


class ExecutionBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveState:
    balances: dict[str, Decimal]
    rates: dict[str, Decimal]
    transfers: list[dict[str, Any]]
    new_beneficiaries: list[dict[str, Any]]
    observed_at: datetime


class Executor:
    def __init__(
        self,
        database: db.Database,
        client: AirwallexClient,
        *,
        policy_path: Path,
        key_dir: Path,
        seal_dir: Path,
        halt_file: Path,
        lock_file: Path,
    ) -> None:
        self.database, self.client = database, client
        self.policy_path, self.key_dir, self.seal_dir = policy_path, key_dir, seal_dir
        self.halt_file, self.lock_file = halt_file, lock_file
        self.passkeys = signing.Passkeys(
            rp_id=os.environ.get("WEBAUTHN_RP_ID", "localhost"),
            origin=os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:8000"),
        )
        self.key = audit.load_private_key(key_dir / "audit_ed25519.pem")
        self.public = Ed25519PublicKey.from_public_bytes((key_dir / "audit.public").read_bytes())
        if (
            self.key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            != (key_dir / "audit.public").read_bytes()
        ):
            raise ExecutionBlockedError(
                "Audit signing key does not match its pinned public identity"
            )
        self.vault = DetailVault(key_dir / "details.key")

    def _trust(self, conn: db.Connection) -> None:
        if not audit.verify_checkpoints(conn, self.seal_dir, self.public).ok:
            raise ExecutionBlockedError("Audit checkpoint verification failed")
        try:
            trust.verify_roster(conn, self.key_dir, self.public)
        except Exception:
            raise ExecutionBlockedError("Registered operator trust could not be verified") from None

    def _live(self, conn: db.Connection) -> LiveState:
        db.assert_no_write_lock(conn, doing="read live Airwallex execution guards")
        balances = {row.currency: row.available_amount for row in self.client.get_balances()}
        currencies = set(balances) | {
            row[0] for row in conn.execute("SELECT DISTINCT currency FROM obligation")
        }
        rates = self.client.usd_risk_rates(currencies)
        transfers = self.client.list_transfers(start=(utcnow() - timedelta(days=366)).isoformat())
        today = (
            utcnow()
            .astimezone(ZoneInfo("Asia/Kolkata"))
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        beneficiaries = list(
            self.client.list_items("/beneficiaries", from_date=today.astimezone(UTC).isoformat())
        )
        if self.client.list_rfis():
            raise ExecutionBlockedError(
                "Airwallex has action-required RFIs; resolve them in its console"
            )
        if self.client.clock_skew_s is None or abs(self.client.clock_skew_s) > 120:
            raise ExecutionBlockedError("Airwallex clock could not be verified within 120 seconds")
        return LiveState(balances, rates, transfers, beneficiaries, utcnow())

    def _caps(
        self,
        conn: db.Connection,
        terms: packets.PaymentPacket,
        live: LiveState,
        policy: LoadedPolicy,
        beneficiary_id: str | None,
    ) -> None:
        item = terms.items[0]
        now = utcnow()
        day = (
            now.astimezone(ZoneInfo("Asia/Kolkata"))
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(UTC)
        )
        rows: dict[str, dict[str, Any]] = {}
        for transfer in live.transfers:
            currency = transfer["transfer_currency"]
            amount = Decimal(str(transfer["transfer_amount"]))
            created = datetime.fromisoformat(transfer["created_at"].replace("Z", "+00:00"))
            if (
                not amount.is_finite()
                or amount < 0
                or currency not in live.rates
                or created.tzinfo is None
            ):
                raise ExecutionBlockedError("Provider cap data is incomplete")
            request = str(transfer.get("request_id") or "provider:" + transfer["id"])
            rows[request] = {
                "amount": amount * live.rates[currency],
                "created": created,
                "beneficiary_id": transfer.get("beneficiary_id"),
                "run_id": None,
                "signers": set(),
            }
        for intent in conn.execute(
            "SELECT e.*,p.canonical_json FROM execution_intent e JOIN "
            "approval_packet p ON p.id=e.packet_id "
            "WHERE e.kind='TRANSFER' AND e.state<>'REJECTED'"
        ):
            self._intent(conn, intent["id"])
            payload = json.loads(intent["canonical_payload"])
            packet_data = json.loads(intent["canonical_json"])
            request = intent["request_id"]
            if request not in rows:
                rows[request] = {
                    "amount": Decimal(payload["transfer_amount"])
                    * live.rates[payload["transfer_currency"]],
                    "created": datetime.fromisoformat(intent["created_at"]),
                    "beneficiary_id": payload["beneficiary_id"],
                }
            rows[request]["run_id"] = packet_data["run_id"]
            if rows[request].get("beneficiary_id") not in {None, payload["beneficiary_id"]}:
                raise ExecutionBlockedError("Provider payee differs from audited payment history")
            rows[request]["beneficiary_id"] = payload["beneficiary_id"]
            rows[request]["signers"] = {
                json.loads(r[0])["user_id"]
                for r in conn.execute(
                    "SELECT payload_json FROM audit_log WHERE kind='approval.signed' "
                    "AND json_extract(payload_json,'$.packet_id')=? AND seq < "
                    "(SELECT MIN(seq) FROM audit_log WHERE kind='execution.intent' "
                    "AND json_extract(payload_json,'$.intent_id')=?)",
                    (intent["packet_id"], intent["id"]),
                )
            }
        rows.pop(item.request_id, None)
        daily = [row for row in rows.values() if row["created"] >= day]
        # Unattributed provider transfers conservatively count against this run
        # and its signers; no invented owner or reset by deleting the local DB.
        run = [
            row
            for row in rows.values()
            if row.get("run_id") in {None, terms.run_id} and row["created"] >= day
        ]
        amount_usd = Decimal(item.transfer_amount) * live.rates[item.transfer_currency]
        limits = policy.policy["limits"]
        if (
            sum((r["amount"] for r in daily), Decimal(0)) + amount_usd
            > Decimal(limits["per_day"]["all_usd"])
            or len(daily) + 1 > limits["per_day"]["max_payments"]
            or sum((r["amount"] for r in run), Decimal(0)) + amount_usd
            > Decimal(limits["per_run"]["all_usd"])
            or len(run) + 1 > limits["per_run"]["max_payments"]
        ):
            raise ExecutionBlockedError("Daily or per-run payment cap exceeded")
        runs = conn.execute(
            "SELECT COUNT(*) FROM run WHERE started_at>=?", (day.isoformat(),)
        ).fetchone()[0]
        if runs > limits["per_day"]["max_runs"]:
            raise ExecutionBlockedError("Daily run cap exceeded")
        if beneficiary_id:
            vendor_id = conn.execute(
                "SELECT vendor_id FROM obligation WHERE id=?", (item.obligation_id,)
            ).fetchone()[0]
            vendor_beneficiaries = {
                r[0]
                for r in conn.execute(
                    "SELECT beneficiary_id FROM beneficiary_map WHERE payee_version_id IN "
                    "(SELECT id FROM payee_version WHERE vendor_id=?)",
                    (vendor_id,),
                )
            }
            recent = [
                row
                for row in rows.values()
                if (
                    row.get("beneficiary_id") is None
                    or row.get("beneficiary_id") in vendor_beneficiaries
                )
                and row["created"] >= now - timedelta(hours=24)
            ]
            if len(recent) >= limits["per_payee_24h"]["max_payments"]:
                raise ExecutionBlockedError("Payee payment velocity cap exceeded")
            aggregate = sum(
                (
                    r["amount"]
                    for r in rows.values()
                    if (
                        r.get("beneficiary_id") is None
                        or r.get("beneficiary_id") in vendor_beneficiaries
                    )
                    and r["created"] >= now - timedelta(days=7)
                ),
                Decimal(0),
            )
            if (
                aggregate + amount_usd
                >= Decimal(policy.policy["tiers"]["t2_payee_7d_aggregate_usd"])
                and terms.required_approvers < 2
            ):
                raise ExecutionBlockedError("Payee seven-day aggregate requires two approvals")
        for signer in conn.execute(
            "SELECT approver_id FROM approval_signature WHERE "
            "packet_id=(SELECT id FROM approval_packet WHERE sha256=?)",
            (hashlib.sha256(audit.canonical_json(terms.model_dump()).encode()).hexdigest(),),
        ):
            used = sum(
                (r["amount"] for r in daily if not r.get("signers") or signer[0] in r["signers"]),
                Decimal(0),
            )
            if used + amount_usd > Decimal(limits["per_approver_day_usd"]):
                raise ExecutionBlockedError("Approver daily payment cap exceeded")

    def _guard(
        self,
        conn: db.Connection,
        packet_id: str,
        live: LiveState,
        beneficiary_id: str | None = None,
    ) -> tuple[packets.PaymentPacket, BankDetails]:
        killswitch.load(conn, self.halt_file).guard()
        if utcnow() - live.observed_at > timedelta(seconds=60):
            raise ExecutionBlockedError("Live execution checks are stale")
        policy = load_runtime_policy(conn, self.policy_path, self.passkeys)
        row = signing.packet(conn, packet_id, allow_consumed=True)
        self.passkeys.verify_stored(conn, packet_id, allow_consumed=True)
        signed = packets.PaymentPacket.model_validate_json(row["canonical_json"])
        if datetime.fromisoformat(signed.expires_at) <= utcnow() or datetime.fromisoformat(
            signed.created_at
        ) > utcnow() + timedelta(seconds=120):
            raise ExecutionBlockedError(
                "Signed payment validity window is expired or in the future"
            )
        item = signed.items[0]
        for prior in conn.execute(
            "SELECT * FROM transfer_attempt WHERE obligation_id=? AND request_id<>?",
            (item.obligation_id, item.request_id),
        ):
            observed = [r for r in live.transfers if r.get("request_id") == prior["request_id"]]
            if prior["wt_state"] == "REJECTED" and observed:
                raise ExecutionBlockedError(
                    "A previously rejected attempt exists at Airwallex; "
                    "reconcile before replacement"
                )
            if prior["wt_state"] in {"FINAL", "CANCELLED_FAILED"}:
                expected = "PAID" if prior["wt_state"] == "FINAL" else "CANCELLED"
                if len(observed) != 1 or observed[0].get("status") != expected:
                    raise ExecutionBlockedError(
                        "Earlier attempt is not confirmed terminal at Airwallex"
                    )
        rebuilt = packets.build_payment(
            conn,
            obligation_id=item.obligation_id,
            payee_id=item.payee_version_id,
            tranche_no=item.tranche_no,
            run_id=signed.run_id,
            policy=policy,
            passkeys=self.passkeys,
            vault=self.vault,
            rates=live.rates,
            attempt_no=item.attempt_no,
            own_request_id=item.request_id,
            approval_created_at=datetime.fromisoformat(signed.created_at),
        )
        if rebuilt != signed:
            raise ExecutionBlockedError(
                "Live payment terms differ from the signed packet; re-plan and re-sign"
            )
        local = utcnow().astimezone(
            ZoneInfo(
                {
                    "ACH": "America/New_York",
                    "FPS": "Europe/London",
                    "SEPA": "Europe/Berlin",
                    "SWIFT": "America/New_York",
                }[item.rail]
            )
        )
        cutoff = policy.policy["rails"]["cutoff_local_time"][item.rail]
        if local.date().isoformat() > item.latest_send_date or (
            local.date().isoformat() == item.latest_send_date and local.strftime("%H:%M") >= cutoff
        ):
            raise ExecutionBlockedError("Latest send date or configured rail cutoff has passed")
        self._caps(conn, signed, live, policy, beneficiary_id)
        amount = Decimal(item.transfer_amount)
        fee_reservation = Decimal(policy.policy["rails"]["fee_reservation_usd"][item.rail])
        available = live.balances.get(item.source_currency, Decimal(0))
        if available < amount + fee_reservation / live.rates[item.source_currency]:
            raise ExecutionBlockedError(
                "Insufficient available wallet balance including fee reservation"
            )
        total_usd = sum(
            (value * live.rates[currency] for currency, value in live.balances.items()), Decimal(0)
        )
        if total_usd - amount * live.rates[item.source_currency] - fee_reservation < Decimal(
            policy.policy["reserve_floor"]["USD"]
        ):
            raise ExecutionBlockedError("Execution reserve floor would be breached")
        for currency, floor in policy.policy["reserve_floor"].items():
            if currency == "USD":
                continue  # Base-currency reserve is the aggregate USD-equivalent floor above.
            if live.balances.get(currency, Decimal(0)) - (
                amount if currency == item.source_currency else Decimal(0)
            ) < Decimal(floor):
                raise ExecutionBlockedError("Currency reserve floor would be breached")
        payee = conn.execute(
            "SELECT details_ref FROM payee_version WHERE id=?", (item.payee_version_id,)
        ).fetchone()
        return signed, self.vault.load(conn, payee["details_ref"])

    def _claim(
        self,
        conn: db.Connection,
        packet_id: str,
        *,
        kind: str,
        request_id: str,
        payload: dict[str, Any],
        live: LiveState,
        beneficiary_id: str | None = None,
    ) -> tuple[str, bool]:
        raw = audit.canonical_json(payload)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with db.transaction(conn):
            terms, _ = self._guard(conn, packet_id, live, beneficiary_id)
            existing = conn.execute(
                "SELECT id,canonical_payload FROM execution_intent WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if existing:
                if existing["canonical_payload"] != raw:
                    raise ExecutionBlockedError(
                        "Idempotency key is already bound to different terms"
                    )
                return existing["id"], False
            intent_id = str(uuid4())
            seq = audit.log_intent(
                conn,
                "execution.intent",
                {
                    "intent_id": intent_id,
                    "packet_id": packet_id,
                    "kind": kind,
                    "request_id": request_id,
                    "payload_sha256": digest,
                    "packet_sha256": hashlib.sha256(
                        audit.canonical_json(terms.model_dump()).encode()
                    ).hexdigest(),
                },
            )
            consumed = conn.execute(
                "SELECT intent_audit_seq FROM approval_consumption WHERE packet_id=?", (packet_id,)
            ).fetchone()
            if not consumed:
                conn.execute(
                    "INSERT INTO "
                    "approval_consumption(packet_id,consumed_at,intent_audit_seq) "
                    "VALUES(?,?,?)",
                    (packet_id, utcnow().isoformat(), seq),
                )
                conn.execute("UPDATE approval_packet SET state='CONSUMED' WHERE id=?", (packet_id,))
            elif (
                kind != "TRANSFER"
                or not conn.execute(
                    "SELECT 1 FROM execution_intent WHERE packet_id=? AND "
                    "kind='BENEFICIARY' AND state='SUBMITTED'",
                    (packet_id,),
                ).fetchone()
            ):
                raise ExecutionBlockedError("Approval already consumed")
            now = utcnow().isoformat()
            conn.execute(
                "INSERT INTO "
                "execution_intent(id,packet_id,kind,request_id,"
                "canonical_payload,payload_sha256,state,created_at,"
                "updated_at) "
                "VALUES(?,?,?,?,?,?,'PREPARED',?,?)",
                (intent_id, packet_id, kind, request_id, raw, digest, now, now),
            )
            if kind == "TRANSFER":
                item = terms.items[0]
                conn.execute(
                    "INSERT INTO "
                    "transfer_attempt(id,obligation_id,tranche_no,attempt_no,"
                    "request_id,wt_state,created_at,updated_at,payee_version_id,"
                    "packet_id,run_id,amount_usd) "
                    "VALUES(?,?,?,?,?,'SUBMITTING',?,?,?,?,?,?)",
                    (
                        str(uuid4()),
                        item.obligation_id,
                        item.tranche_no,
                        item.attempt_no,
                        request_id,
                        now,
                        now,
                        item.payee_version_id,
                        packet_id,
                        terms.run_id,
                        str(Decimal(item.transfer_amount) * live.rates[item.transfer_currency]),
                    ),
                )
        # Seal the INTENT before the call, outside SQLite's write transaction.
        audit.write_checkpoint(conn, self.seal_dir, self.key, reason="intent-" + intent_id)
        return intent_id, True

    def _intent(self, conn: db.Connection, identifier: str) -> db.sqlite3.Row:
        row: Row | None = conn.execute(
            "SELECT * FROM execution_intent WHERE id=?", (identifier,)
        ).fetchone()
        if (
            not row
            or hashlib.sha256(row["canonical_payload"].encode()).hexdigest()
            != row["payload_sha256"]
        ):
            raise ExecutionBlockedError("Execution intent terms were modified")
        evidence = conn.execute(
            "SELECT payload_json FROM audit_log WHERE kind='execution.intent' "
            "AND json_extract(payload_json,'$.intent_id')=? ORDER BY seq LIMIT 1",
            (identifier,),
        ).fetchone()
        if not evidence:
            raise ExecutionBlockedError("Execution intent has no matching audit evidence")
        bound = json.loads(evidence["payload_json"])
        for field in ("packet_id", "kind", "request_id", "payload_sha256"):
            if bound.get(field) != row[field]:
                raise ExecutionBlockedError("Execution intent differs from audited terms")
        packet_json = conn.execute(
            "SELECT canonical_json FROM approval_packet WHERE id=?", (row["packet_id"],)
        ).fetchone()[0]
        if hashlib.sha256(packet_json.encode()).hexdigest() != bound["packet_sha256"]:
            raise ExecutionBlockedError("Consumed approval differs from the audited packet")
        return row

    def _result(
        self,
        conn: db.Connection,
        identifier: str,
        state: str,
        *,
        provider_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with db.transaction(conn):
            conn.execute(
                "UPDATE execution_intent SET "
                "state=?,provider_id=?,last_error=?,updated_at=? WHERE id=?",
                (state, provider_id, error, utcnow().isoformat(), identifier),
            )
            audit.log_result(
                conn, "execution.result", {"intent_id": identifier, "state": state, "error": error}
            )

    def _accept_transfer(
        self, conn: db.Connection, intent: db.sqlite3.Row, result: Transfer
    ) -> None:
        payload = json.loads(intent["canonical_payload"])
        data = result.model_dump(mode="json")
        if result.request_id != payload["request_id"]:
            raise ExecutionBlockedError("Provider request ID mismatches execution intent")
        if "transfer_amount" not in data or Decimal(str(data["transfer_amount"])) != Decimal(
            payload["transfer_amount"]
        ):
            raise ExecutionBlockedError("Provider payout amount mismatches execution intent")
        for key in ("transfer_currency", "source_currency"):
            if key not in data or str(data[key]) != payload[key]:
                raise ExecutionBlockedError("Provider payout terms mismatch execution intent")
        if data.get("beneficiary_id") != payload["beneficiary_id"]:
            packet_json = conn.execute(
                "SELECT canonical_json FROM approval_packet WHERE id=?", (intent["packet_id"],)
            ).fetchone()[0]
            payee_id = json.loads(packet_json)["items"][0]["payee_version_id"]
            details_ref = conn.execute(
                "SELECT details_ref FROM payee_version WHERE id=?", (payee_id,)
            ).fetchone()[0]
            if not self.vault.load(conn, details_ref).matches_provider(data):
                raise ExecutionBlockedError("Provider beneficiary does not match execution intent")
        with db.transaction(conn):
            self._result(conn, intent["id"], "SUBMITTED", provider_id=result.id)
            conn.execute(
                "UPDATE transfer_attempt SET "
                "transfer_id=?,awx_status=?,wt_state=?,updated_at=? WHERE "
                "request_id=?",
                (
                    result.id,
                    result.status,
                    "PAID_PROVISIONAL" if result.status == "PAID" else "SUBMITTING",
                    utcnow().isoformat(),
                    result.request_id,
                ),
            )
            conn.execute(
                "INSERT INTO "
                "transfer_observation(id,transfer_id,observed_at,awx_status,"
                "raw_json) VALUES(?,?,?,?,?)",
                (
                    str(uuid4()),
                    result.id,
                    utcnow().isoformat(),
                    result.status,
                    self.vault.encrypt_json(data),
                ),
            )
        audit.write_checkpoint(conn, self.seal_dir, self.key, reason="result-" + intent["id"])

    def _recover_one(self, conn: db.Connection, intent: db.sqlite3.Row) -> str:
        payload = json.loads(intent["canonical_payload"])
        db.assert_no_write_lock(conn, doing="resolve uncertain execution intent")
        if intent["kind"] == "TRANSFER":
            result = self.client.find_transfer(
                intent["request_id"], from_created_at=intent["created_at"]
            )
            if result:
                self._accept_transfer(conn, intent, result)
                return "SUBMITTED"
        elif intent["kind"] == "BENEFICIARY":
            found = self.client.find_beneficiary(payload["nickname"])
            if found:
                self._accept_beneficiary(conn, intent, found)
                return "SUBMITTED"
        self._result(conn, intent["id"], "AMBIGUOUS", error="not_found_after_uncertain_request")
        if intent["kind"] == "TRANSFER":
            conn.execute(
                "UPDATE transfer_attempt SET wt_state='AMBIGUOUS',updated_at=? WHERE request_id=?",
                (utcnow().isoformat(), intent["request_id"]),
            )
        return "AMBIGUOUS"

    def _accept_beneficiary(
        self, conn: db.Connection, intent: db.sqlite3.Row, result: dict[str, Any]
    ) -> str:
        terms = packets.PaymentPacket.model_validate_json(
            conn.execute(
                "SELECT canonical_json FROM approval_packet WHERE id=?", (intent["packet_id"],)
            ).fetchone()[0]
        )
        item = terms.items[0]
        payee = conn.execute(
            "SELECT details_ref FROM payee_version WHERE id=?", (item.payee_version_id,)
        ).fetchone()
        details = self.vault.load(conn, payee["details_ref"])
        if (
            result.get("nickname") != item.beneficiary_nickname
            or not details.matches_provider(result)
            or not result.get("id")
        ):
            raise ExecutionBlockedError(
                "Provider beneficiary details differ from signed bank version"
            )
        with db.transaction(conn):
            conn.execute(
                "INSERT INTO "
                "beneficiary_map(payee_version_id,beneficiary_id,nickname,"
                "created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(payee_version_id) DO NOTHING",
                (
                    item.payee_version_id,
                    result["id"],
                    item.beneficiary_nickname,
                    utcnow().isoformat(),
                ),
            )
            mapped = conn.execute(
                "SELECT beneficiary_id FROM beneficiary_map WHERE payee_version_id=?",
                (item.payee_version_id,),
            ).fetchone()[0]
            if mapped != result["id"]:
                raise ExecutionBlockedError("Beneficiary mapping conflict")
            self._result(conn, intent["id"], "SUBMITTED", provider_id=result["id"])
        return str(result["id"])

    def recover(self) -> dict[str, str]:
        with exclusive_process(self.lock_file):
            conn = self.database.connection()
            self._trust(conn)
            outcomes = {}
            rows = conn.execute(
                "SELECT id FROM execution_intent WHERE state IN "
                "('PREPARED','AMBIGUOUS') ORDER BY created_at"
            ).fetchall()
            for row in rows:
                intent = self._intent(conn, row["id"])
                outcomes[intent["id"]] = self._recover_one(conn, intent)
            return outcomes

    def execute(self, packet_id: str) -> str:
        with exclusive_process(self.lock_file):
            conn = self.database.connection()
            try:
                self._trust(conn)
                old = conn.execute(
                    "SELECT id,state FROM execution_intent WHERE packet_id=? AND kind='TRANSFER'",
                    (packet_id,),
                ).fetchone()
                if old:
                    return (
                        self._recover_one(conn, self._intent(conn, old["id"]))
                        if old["state"] in {"PREPARED", "AMBIGUOUS"}
                        else str(old["state"])
                    )
                live = self._live(conn)
                terms, details = self._guard(conn, packet_id, live)
                item = terms.items[0]
                mapped = conn.execute(
                    "SELECT beneficiary_id FROM beneficiary_map WHERE payee_version_id=?",
                    (item.payee_version_id,),
                ).fetchone()
                if mapped:
                    beneficiary_id = mapped[0]
                else:
                    prior = conn.execute(
                        "SELECT id,state FROM execution_intent WHERE packet_id=? AND "
                        "kind='BENEFICIARY'",
                        (packet_id,),
                    ).fetchone()
                    if prior:
                        intent = self._intent(conn, prior["id"])
                        if (
                            prior["state"] != "SUBMITTED"
                            and self._recover_one(conn, intent) != "SUBMITTED"
                        ):
                            return "AMBIGUOUS"
                        beneficiary_id = conn.execute(
                            "SELECT beneficiary_id FROM beneficiary_map WHERE payee_version_id=?",
                            (item.payee_version_id,),
                        ).fetchone()[0]
                    else:
                        existing = self.client.find_beneficiary(item.beneficiary_nickname)
                        if existing:
                            if not details.matches_provider(existing):
                                raise ExecutionBlockedError(
                                    "Existing beneficiary nickname maps to different bank details"
                                )
                            beneficiary_id = existing["id"]
                            with db.transaction(conn):
                                conn.execute(
                                    "INSERT INTO "
                                    "beneficiary_map(payee_version_id,beneficiary_id,nickname,"
                                    "created_at) VALUES(?,?,?,?)",
                                    (
                                        item.payee_version_id,
                                        beneficiary_id,
                                        item.beneficiary_nickname,
                                        utcnow().isoformat(),
                                    ),
                                )
                        else:
                            policy = load_runtime_policy(conn, self.policy_path, self.passkeys)
                            pending = conn.execute(
                                "SELECT COUNT(*) FROM execution_intent WHERE kind='BENEFICIARY' "
                                "AND state IN ('PREPARED','AMBIGUOUS')"
                            ).fetchone()[0]
                            if (
                                len(live.new_beneficiaries) + pending
                                >= policy.policy["limits"]["per_day"]["max_new_beneficiaries"]
                            ):
                                raise ExecutionBlockedError(
                                    "Daily beneficiary-creation cap exceeded"
                                )
                            payload = details.beneficiary_payload(item.beneficiary_nickname)
                            self.client.beneficiary_schema(
                                {
                                    "entity_type": "COMPANY",
                                    "bank_country_code": details.country,
                                    "account_currency": details.currency,
                                    "transfer_method": details.method,
                                }
                            )
                            self.client.validate_beneficiary(
                                {key: value for key, value in payload.items() if key != "nickname"}
                            )
                            namespace = conn.execute(
                                "SELECT value FROM schema_meta WHERE key='request_namespace'"
                            ).fetchone()[0]
                            rejected_count = conn.execute(
                                "SELECT COUNT(*) FROM execution_intent WHERE kind='BENEFICIARY' "
                                "AND state='REJECTED' AND json_extract(canonical_payload,"
                                "'$.nickname')=?",
                                (item.beneficiary_nickname,),
                            ).fetchone()[0]
                            identifier, fresh = self._claim(
                                conn,
                                packet_id,
                                kind="BENEFICIARY",
                                request_id=str(
                                    uuid5(
                                        UUID(namespace),
                                        "beneficiary:"
                                        + item.payee_version_id
                                        + ":a"
                                        + str(rejected_count + 1),
                                    )
                                ),
                                payload=payload,
                                live=live,
                            )
                            intent = self._intent(conn, identifier)
                            if not fresh:
                                state = self._recover_one(conn, intent)
                                return "BENEFICIARY_READY" if state == "SUBMITTED" else state
                            self._guard(conn, packet_id, live)
                            db.assert_no_write_lock(conn, doing="create approved beneficiary")
                            try:
                                beneficiary_id = self._accept_beneficiary(
                                    conn, intent, self.client.create_beneficiary(payload)
                                )
                            except ProviderError as exc:
                                if exc.category == "ambiguous":
                                    state = self._recover_one(conn, intent)
                                    return "BENEFICIARY_READY" if state == "SUBMITTED" else state
                                self._result(conn, identifier, "REJECTED", error=exc.category)
                                return "REJECTED"
                # Re-read after beneficiary creation; no balance or policy
                # snapshot taken before a network mutation authorizes the payout.
                live = self._live(conn)
                terms, details = self._guard(conn, packet_id, live, beneficiary_id)
                if not details.matches_provider(self.client.beneficiary(beneficiary_id)):
                    raise ExecutionBlockedError("Live beneficiary bank details changed")
                transfer_request = TransferRequest(
                    request_id=item.request_id,
                    beneficiary_id=beneficiary_id,
                    transfer_amount=item.transfer_amount,
                    transfer_currency=item.transfer_currency,
                    source_currency=item.source_currency,
                    transfer_method=item.transfer_method,
                    reason=item.reason,
                    reference=item.reference,
                    swift_charge_option=item.swift_charge_option,
                    fee_paid_by=item.fee_paid_by,
                )
                identifier, fresh = self._claim(
                    conn,
                    packet_id,
                    kind="TRANSFER",
                    request_id=item.request_id,
                    payload=transfer_request.model_dump(exclude_none=True),
                    live=live,
                    beneficiary_id=beneficiary_id,
                )
                intent = self._intent(conn, identifier)
                if not fresh:
                    return self._recover_one(conn, intent)
                found = self.client.find_transfer(
                    item.request_id, from_created_at=intent["created_at"]
                )
                if found:
                    self._accept_transfer(conn, intent, found)
                    return "SUBMITTED"
                self._guard(conn, packet_id, live, beneficiary_id)
                db.assert_no_write_lock(conn, doing="submit approved payout")
                try:
                    self._accept_transfer(
                        conn, intent, self.client.create_transfer(transfer_request)
                    )
                    return "SUBMITTED"
                except ProviderError as exc:
                    if exc.category in {"ambiguous", "duplicate_request_id"}:
                        return self._recover_one(conn, intent)
                    self._result(conn, identifier, "REJECTED", error=exc.category)
                    conn.execute(
                        "UPDATE transfer_attempt SET wt_state='REJECTED' WHERE request_id=?",
                        (item.request_id,),
                    )
                    return "REJECTED"
            except (
                ExecutionBlockedError,
                signing.SigningError,
                packets.PaymentBlockedError,
                PolicyError,
                db.DatabaseBusyError,
                audit.AuditWriteError,
            ) as exc:
                try:
                    killswitch.trip(
                        conn, str(exc), origin="executor_guard", halt_file=self.halt_file
                    )
                except Exception:
                    # An audit/database failure cannot be allowed to leave the
                    # next worker free to act. Filesystem failure still propagates.
                    self.halt_file.parent.mkdir(parents=True, exist_ok=True)
                    self.halt_file.write_text(
                        "Executor stopped: inspect audit/database health", encoding="utf-8"
                    )
                raise
