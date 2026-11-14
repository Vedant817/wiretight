"""Supplier/invoice/evidence intake and passkey-signed manual compliance review."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response

from app.api import access
from app.api.operators import CeremonyBody
from app.config import WebSettings
from app.core import (
    audit,
    db,
    evidence,
    intake,
    lock,
    operators,
    record_signing,
    runtime_policy,
    signing,
)
from app.core.bank_details import DetailVault
from app.core.policy import PolicyError


def router(database: db.Database, passkeys: signing.Passkeys, settings: WebSettings) -> APIRouter:
    routes = APIRouter(prefix="/api")

    def identity(request: Request, *, mutate: bool = False) -> operators.Session:
        return access.identity(request, database, passkeys.origin, mutate=mutate)

    def vault() -> DetailVault:
        try:
            return DetailVault(Path(settings.app_key_dir) / "details.key")
        except (OSError, ValueError):
            raise HTTPException(
                503, "Installation encryption key unavailable; complete local setup"
            ) from None

    @routes.post("/evidence", status_code=201)
    async def upload(request: Request) -> dict[str, str | int]:
        session = identity(request, mutate=True)
        try:
            return evidence.store(
                database.connection(),
                vault(),
                session,
                content=await request.body(),
                filename=request.headers.get("x-filename", ""),
                media_type=request.headers.get("content-type", "").split(";")[0].lower(),
            )
        except evidence.EvidenceError as exc:
            raise HTTPException(422, str(exc)) from None

    @routes.get("/evidence/{digest}")
    def download(digest: str, request: Request) -> Response:
        identity(request)
        try:
            row, content = evidence.read(database.connection(), vault(), digest)
        except evidence.EvidenceError as exc:
            raise HTTPException(404, str(exc)) from None
        # Always download; uploaded content must never become an executable app page.
        return Response(
            content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{row["filename"]}"',
                "Content-Security-Policy": "sandbox; default-src 'none'",
            },
        )

    @routes.get("/suppliers")
    def suppliers(request: Request) -> list[dict[str, Any]]:
        identity(request)
        return [
            dict(row)
            for row in database.connection()
            .execute(
                "SELECT id,display_name,legal_name_norm,category,flags,created_at FROM vendor "
                "ORDER BY created_at DESC,id LIMIT 100"
            )
            .fetchall()
        ]

    @routes.post("/suppliers", status_code=201)
    def add_supplier(body: intake.VendorInput, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        try:
            policy, _ = runtime_policy.validated_policy(
                database.connection(), settings.app_policy_path
            )
            identifier = intake.add_vendor(database.connection(), session, body, policy)
        except (OSError, PolicyError):
            raise HTTPException(503, "Installation policy unavailable or invalid") from None
        except intake.IntakeError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"vendor_id": identifier}

    @routes.get("/suppliers/{vendor_id}/contacts")
    def contacts(vendor_id: str, request: Request) -> list[dict[str, Any]]:
        identity(request)
        return [
            dict(row)
            for row in database.connection()
            .execute(
                "SELECT id,kind,value,provenance,provenance_sha256,created_at,changed_at,"
                "active,imported_at "
                "FROM vendor_contact WHERE vendor_id=? ORDER BY created_at DESC,id LIMIT 100",
                (vendor_id,),
            )
            .fetchall()
        ]

    @routes.post("/suppliers/{vendor_id}/contacts", status_code=201)
    def add_contact(vendor_id: str, body: intake.ContactInput, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        try:
            identifier = intake.add_contact(database.connection(), session, vendor_id, body)
        except (intake.IntakeError, evidence.EvidenceError) as exc:
            raise HTTPException(409, str(exc)) from None
        return {"contact_id": identifier}

    @routes.get("/suppliers/{vendor_id}/banks")
    def banks(vendor_id: str, request: Request) -> list[dict[str, Any]]:
        identity(request)
        return [
            dict(row)
            for row in database.connection()
            .execute(
                "SELECT id,vendor_id,masked,fingerprint,rail,currency,status,"
                "cooling_off_until,created_at "
                "FROM payee_version WHERE vendor_id=? ORDER BY created_at DESC,id LIMIT 100",
                (vendor_id,),
            )
            .fetchall()
        ]

    @routes.post("/suppliers/{vendor_id}/bank-changes", status_code=201)
    def bank_change(vendor_id: str, body: intake.BankInput, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        try:
            return intake.propose_bank(database.connection(), vault(), session, vendor_id, body)
        except (intake.IntakeError, evidence.EvidenceError, lock.ChangeRequestConflictError) as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.get("/invoices")
    def invoices(request: Request) -> list[dict[str, Any]]:
        identity(request)
        return [
            dict(row)
            for row in database.connection()
            .execute(
                "SELECT id,vendor_id,invoice_no_raw,amount,currency,due_date,state,flags,"
                "created_at "
                "FROM obligation ORDER BY created_at DESC,id LIMIT 100"
            )
            .fetchall()
        ]

    @routes.post("/invoices", status_code=201)
    def add_invoice(body: intake.InvoiceInput, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        try:
            identifier = intake.add_invoice(database.connection(), session, body)
        except (intake.IntakeError, evidence.EvidenceError) as exc:
            raise HTTPException(409, str(exc)) from None
        return {"obligation_id": identifier, "state": "READY"}

    @routes.get("/banks/{payee_id}/reviews")
    def reviews(payee_id: str, request: Request) -> list[dict[str, Any]]:
        identity(request)
        return [
            dict(row)
            for row in database.connection()
            .execute(
                "SELECT * FROM compliance_review WHERE payee_version_id=? "
                "ORDER BY created_at DESC,id LIMIT 100",
                (payee_id,),
            )
            .fetchall()
        ]

    @routes.post("/banks/{payee_id}/reviews/options")
    def review_options(payee_id: str, body: intake.ReviewInput, request: Request) -> dict[str, Any]:
        session = identity(request, mutate=True)
        try:
            with database.transaction() as conn:
                record = intake.review_record(conn, session, payee_id, body)
                return record_signing.begin_record(
                    conn,
                    session,
                    passkeys,
                    purpose="CALLBACK",
                    subject_id="review:" + record["id"],
                    record=record,
                )
        except (intake.IntakeError, evidence.EvidenceError, signing.SigningError) as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.post("/banks/{payee_id}/reviews/finish", status_code=201)
    def review_finish(payee_id: str, body: CeremonyBody, request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        try:
            with database.transaction() as conn:
                ceremony = conn.execute(
                    "SELECT * FROM signing_challenge WHERE id=?", (body.ceremony_id,)
                ).fetchone()
                if not ceremony or not ceremony["record_json"]:
                    raise signing.SigningError("Review ceremony unavailable")
                record = json.loads(ceremony["record_json"])
                if (
                    record.get("kind") != "COMPLIANCE_REVIEW"
                    or record.get("payee_version_id") != payee_id
                ):
                    raise signing.SigningError("Review ceremony covers a different decision")
                current = intake.review_record(
                    conn,
                    session,
                    payee_id,
                    intake.ReviewInput.model_validate(
                        {key: record[key] for key in intake.ReviewInput.model_fields}
                    ),
                )
                if any(
                    record[key] != value
                    for key, value in current.items()
                    if key not in {"id", "created_at"}
                ):
                    raise signing.SigningError("Bank-detail version changed after review")
                record_signing.finish_record(
                    conn,
                    session,
                    passkeys,
                    purpose="CALLBACK",
                    subject_id="review:" + record["id"],
                    record=record,
                    ceremony_id=body.ceremony_id,
                    credential=body.credential,
                )
                columns = (
                    "id",
                    "payee_version_id",
                    "recorded_by",
                    "result",
                    "source",
                    "evidence_sha256",
                    "checked_at",
                    "created_at",
                    "payee_fingerprint",
                    "details_sha256",
                )
                conn.execute(
                    "INSERT INTO compliance_review("
                    + ",".join(columns)
                    + ") VALUES("
                    + ",".join("?" for _ in columns)
                    + ")",
                    tuple(record[key] for key in columns),
                )
                if record["result"] != "CLEAR":
                    conn.execute(
                        "UPDATE payee_version SET status='COMPLIANCE_HOLD',updated_at=? WHERE id=?",
                        (operators.utcnow().isoformat(), payee_id),
                    )
                    conn.execute(
                        "UPDATE approval_packet SET state='VOID' "
                        "WHERE state IN ('OPEN','APPROVED') AND kind='PAYMENT' "
                        "AND json_extract(canonical_json,'$.items[0].payee_version_id')=?",
                        (payee_id,),
                    )
                audit.append(
                    conn,
                    "compliance.reviewed",
                    {
                        "review_id": record["id"],
                        "payee_version_id": payee_id,
                        "by": session.user_id,
                        "result": record["result"],
                        "evidence_sha256": record["evidence_sha256"],
                    },
                )
                return {"review_id": record["id"], "result": record["result"]}
        except (intake.IntakeError, evidence.EvidenceError, signing.SigningError) as exc:
            raise HTTPException(409, str(exc)) from None

    @routes.post("/provider/refresh", status_code=202)
    def refresh(request: Request) -> dict[str, str]:
        session = identity(request, mutate=True)
        with database.transaction() as conn:
            operators.require_active(conn, session)
            existing = conn.execute(
                "SELECT id FROM provider_job WHERE kind='REFRESH' AND state='PENDING'"
            ).fetchone()
            if existing:
                return {"job_id": existing["id"], "state": "PENDING"}
            identifier = str(uuid4())
            conn.execute(
                "INSERT INTO provider_job(id,kind,requested_by,request_json,state,"
                "created_at,updated_at) "
                "VALUES(?,'REFRESH',?,'{}','PENDING',?,?)",
                (
                    identifier,
                    session.user_id,
                    operators.utcnow().isoformat(),
                    operators.utcnow().isoformat(),
                ),
            )
            audit.append(
                conn, "provider.refresh_requested", {"job_id": identifier, "by": session.user_id}
            )
            return {"job_id": identifier, "state": "PENDING"}

    @routes.get("/provider/jobs/{job_id}")
    def job_status(job_id: str, request: Request) -> dict[str, Any]:
        identity(request)
        row = (
            database.connection()
            .execute(
                "SELECT id,kind,state,result_json,error,created_at,updated_at "
                "FROM provider_job WHERE id=?",
                (job_id,),
            )
            .fetchone()
        )
        if not row:
            raise HTTPException(404, "Provider job not found")
        return dict(row)

    @routes.get("/provider/snapshots")
    def snapshots(request: Request) -> dict[str, Any]:
        identity(request)
        rows = (
            database.connection()
            .execute("SELECT * FROM provider_snapshot ORDER BY kind,subject")
            .fetchall()
        )
        return {
            "snapshots": [dict(row) for row in rows],
            "stale_after_seconds": int(timedelta(minutes=2).total_seconds()),
        }

    return routes
