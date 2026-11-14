"""Real operational views and durable read/plan requests; never provider credentials."""

from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api import access
from app.core import audit, db, operators, signing


class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=100)
    obligation_id: str = Field(min_length=1, max_length=100)
    payee_id: str = Field(min_length=1, max_length=100)
    tranche_no: int = Field(default=1, ge=1, le=2, strict=True)


def router(database: db.Database, passkeys: signing.Passkeys) -> APIRouter:
    routes = APIRouter(prefix="/api")

    def identity(request: Request, *, mutate: bool = False) -> operators.Session:
        return access.identity(request, database, passkeys.origin, mutate=mutate)

    def enqueue(request: Request, operation: str, terms: dict[str, Any]) -> dict[str, str]:
        session = identity(request, mutate=True)
        if session.role != "approver":
            raise HTTPException(403, "Approver role required")
        payload = audit.canonical_json({"operation": operation, **terms})
        with database.transaction() as conn:
            operators.require_active(conn, session)
            prior = conn.execute(
                "SELECT id FROM provider_job WHERE kind='PLAN' AND request_json=? "
                "AND state='PENDING'",
                (payload,),
            ).fetchone()
            identifier = str(prior["id"]) if prior else str(uuid4())
            if not prior:
                now = operators.utcnow().isoformat()
                conn.execute(
                    "INSERT INTO provider_job(id,kind,requested_by,request_json,state,"
                    "created_at,updated_at) VALUES(?,'PLAN',?,?,'PENDING',?,?)",
                    (identifier, session.user_id, payload, now, now),
                )
                audit.append(
                    conn,
                    "operation.requested",
                    {
                        "job_id": identifier,
                        "operation": operation,
                        "by": session.user_id,
                    },
                )
        return {"job_id": identifier, "state": "PENDING"}

    @routes.post("/runs", status_code=202)
    def open_run(request: Request) -> dict[str, str]:
        return enqueue(request, "OPEN_RUN", {})

    @routes.post("/plans", status_code=202)
    def plan(body: PlanInput, request: Request) -> dict[str, str]:
        return enqueue(request, "PLAN_PAYMENT", body.model_dump())

    @routes.post("/runs/{run_id}/{operation}", status_code=202)
    def run_action(
        run_id: str, operation: Literal["reconcile", "close"], request: Request
    ) -> dict[str, str]:
        if len(run_id) > 100:
            raise HTTPException(422, "Invalid run identifier")
        return enqueue(
            request,
            "RECONCILE_RUN" if operation == "reconcile" else "CLOSE_RUN",
            {"run_id": run_id},
        )

    @routes.get("/operations")
    def overview(request: Request) -> dict[str, Any]:
        session = identity(request)
        conn = database.connection()

        def rows(sql: str) -> list[dict[str, Any]]:
            return [dict(r) for r in conn.execute(sql).fetchall()]

        return {
            "server_now": operators.utcnow().isoformat(),
            "role": session.role,
            "runs": rows(
                "SELECT id,started_at,finished_at,state FROM run ORDER BY started_at DESC LIMIT 100"
            ),
            "jobs": rows(
                "SELECT id,kind,state,error,result_json,created_at,updated_at "
                "FROM provider_job ORDER BY created_at DESC LIMIT 100"
            ),
            "executions": rows(
                "SELECT id,kind,packet_id,state,provider_id,updated_at "
                "FROM execution_intent ORDER BY updated_at DESC LIMIT 100"
            ),
            "payments": rows(
                "SELECT id,obligation_id,transfer_id,awx_status,wt_state,"
                "failure_type,first_paid_at,final_at,updated_at FROM transfer_attempt "
                "ORDER BY updated_at DESC LIMIT 100"
            ),
            "cooling": rows(
                "SELECT p.id,p.vendor_id,v.display_name,p.status,p.masked,"
                "p.cooling_off_until FROM payee_version p JOIN vendor v "
                "ON v.id=p.vendor_id WHERE p.status IN ('PROPOSED','ACTIVE_CAPPED') "
                "ORDER BY p.created_at DESC LIMIT 100"
            ),
            "tie_outs": rows(
                "SELECT t.* FROM tie_out t WHERE NOT EXISTS (SELECT 1 FROM "
                "tie_out n WHERE n.run_id=t.run_id AND n.currency=t.currency "
                "AND n.rowid>t.rowid) ORDER BY t.created_at DESC LIMIT 100"
            ),
            "exceptions": rows(
                "SELECT e.* FROM recon_exception e ORDER BY created_at DESC LIMIT 100"
            ),
            "approvals": [
                {**dict(r), "terms": json.loads(r["canonical_json"])}
                for r in conn.execute(
                    "SELECT p.*, (SELECT COUNT(*) FROM approval_signature s WHERE "
                    "s.packet_id=p.id) AS signed_count FROM approval_packet p "
                    "ORDER BY p.created_at DESC LIMIT 100"
                ).fetchall()
            ],
        }

    return routes
