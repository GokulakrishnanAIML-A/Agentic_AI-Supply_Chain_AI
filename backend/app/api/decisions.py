from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_planner
from app.api.schemas import DecisionRequest, DecisionResponse, HITLActionRequest
from app.api.service import execute_decision, to_response
from app.db.models import DecisionRun
from app.db.repositories import append_event
from app.db.session import get_db
from app.validation.validator import validate_override_allocations

router = APIRouter()


@router.post("/decisions", response_model=DecisionResponse)
def create_decision(body: DecisionRequest, db: Session = Depends(get_db)):
    run = execute_decision(db, body.query)
    return to_response(run, db=db)


@router.get("/runs/{run_id}", response_model=DecisionResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(DecisionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return to_response(run, db=db)


@router.post("/decisions/{run_id}/hitl", response_model=DecisionResponse)
def hitl_validation(
    run_id: int,
    body: HITLActionRequest,
    reviewer: str = Depends(current_planner),
    db: Session = Depends(get_db),
):
    """Human-in-the-Loop decision gate.

    Actions:
    - **approve**: Sign off on the plan — records authenticated planner identity and timestamp.
    - **reject**: Flag non-viable plan. If structured modifications are provided, triggers re-optimization
      linked via parent_run_id. If comment-only, marks run rejected without re-running.
    - **override**: Manually adjust allocations — validates against capacity and policy constraints
      before accepting, calculating cost_delta_vs_optimal.
    """
    run = db.get(DecisionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Decision run not found")

    # ── Prevent double-approval / mutation after finalized ──
    if run.hitl_status in ("APPROVED", "APPROVED_WITH_OVERRIDE"):
        raise HTTPException(
            status_code=409,
            detail=f"Run {run_id} already finalised as {run.hitl_status}",
        )

    result = dict(run.result_json or {})
    val = dict(result.get("validation") or {})
    trace = list(result.get("trace") or [])
    now = datetime.now(timezone.utc)

    # ── APPROVE ──
    if body.action == "approve":
        run.hitl_status = "APPROVED"
        run.hitl_reviewed_by = reviewer
        run.hitl_reviewed_at = now
        run.hitl_comments = body.comments
        val["hitl_status"] = "APPROVED"
        val["hitl_planner"] = reviewer
        val["hitl_comments"] = body.comments
        trace.append(
            f"HITL: Plan APPROVED by '{reviewer}' — \"{body.comments}\""
        )
        result["validation"] = val
        result["trace"] = trace
        run.result_json = result
        db.commit()
        db.refresh(run)

        append_event(
            db,
            run_id=run.id,
            actor=reviewer,
            action="APPROVE",
            payload={"comments": body.comments},
        )
        return to_response(run, db=db)

    # ── REJECT ──
    elif body.action == "reject":
        run.hitl_status = "REJECTED"
        run.hitl_reviewed_by = reviewer
        run.hitl_reviewed_at = now
        run.hitl_comments = body.comments
        val["hitl_status"] = "REJECTED"
        val["hitl_planner"] = reviewer
        val["hitl_comments"] = body.comments

        # Check if structured modifications are provided
        has_structured_patch = False
        patch: dict = {}
        if body.reject_reason:
            if body.reject_reason.exclude_suppliers:
                patch["exclude_suppliers"] = body.reject_reason.exclude_suppliers
                has_structured_patch = True
            if body.reject_reason.max_supplier_share is not None:
                patch["max_supplier_share"] = body.reject_reason.max_supplier_share
                has_structured_patch = True
            if body.reject_reason.force_low_risk:
                patch["force_low_risk"] = True
                has_structured_patch = True

        if has_structured_patch:
            trace.append(
                f"HITL: Plan REJECTED by '{reviewer}' with constraints {patch} — \"{body.comments}\". "
                "Re-optimization triggered."
            )
            result["validation"] = val
            result["trace"] = trace
            run.result_json = result
            db.commit()
            db.refresh(run)

            # Re-run pipeline with modified scenario patch, linked to parent
            child_run = execute_decision(db, run.query, patch=patch, parent_id=run.id)

            append_event(
                db,
                run_id=run.id,
                actor=reviewer,
                action="REJECT",
                payload={
                    "comments": body.comments,
                    "patch": patch,
                    "child_run_id": child_run.id,
                },
            )
            return to_response(child_run, rejection_parent_id=run.id, db=db)
        else:
            # Comment-only rejection: record REJECT without creating a duplicate run
            trace.append(
                f"HITL: Plan REJECTED by '{reviewer}' — \"{body.comments}\". No re-optimization requested."
            )
            result["validation"] = val
            result["trace"] = trace
            run.result_json = result
            db.commit()
            db.refresh(run)

            append_event(
                db,
                run_id=run.id,
                actor=reviewer,
                action="REJECT",
                payload={"comments": body.comments, "reason": "comment_only"},
            )
            return to_response(run, db=db)

    # ── OVERRIDE — validate then accept ──
    elif body.action == "override":
        if not body.override_allocations:
            raise HTTPException(
                status_code=422,
                detail="override_allocations required for override action",
            )

        optimal_cost = (result.get("solver") or {}).get("total_cost")
        check = validate_override_allocations(
            result_json=result,
            override_allocations=body.override_allocations,
            optimal_cost=optimal_cost,
            acknowledge_policy_breach=body.acknowledge_policy_breach,
        )

        if not check["ok"]:
            raise HTTPException(
                status_code=422,
                detail=f"Override violates constraints: {check['issues']}",
            )

        run.hitl_status = "APPROVED_WITH_OVERRIDE"
        run.hitl_reviewed_by = reviewer
        run.hitl_reviewed_at = now
        run.hitl_comments = body.comments

        rec = dict(result.get("recommendation") or {})
        rec["supplier_allocation"] = body.override_allocations
        rec["total_cost"] = check["total_cost"]
        rec["cost_delta_vs_optimal"] = check["cost_delta_vs_optimal"]
        rec["delivery_time_hours"] = check["delivery_time_hours"]
        rec["risk_score"] = check["plan_risk"]
        rec["policy_breaches_acknowledged"] = check["policy_breaches_acknowledged"]

        result["recommendation"] = rec
        result["supplier_allocation"] = body.override_allocations
        val["hitl_status"] = "APPROVED_WITH_OVERRIDE"
        val["hitl_planner"] = reviewer
        val["hitl_comments"] = body.comments
        val["cost_delta_vs_optimal"] = check["cost_delta_vs_optimal"]
        val["policy_breaches_acknowledged"] = check["policy_breaches_acknowledged"]

        trace.append(
            f"HITL: Allocations OVERRIDDEN by '{reviewer}' — "
            f"validated. Delta vs optimal: ${check['cost_delta_vs_optimal']:.2f}. \"{body.comments}\""
        )

        result["validation"] = val
        result["trace"] = trace
        run.result_json = result
        db.commit()
        db.refresh(run)

        append_event(
            db,
            run_id=run.id,
            actor=reviewer,
            action="OVERRIDE",
            payload={
                "comments": body.comments,
                "allocations": body.override_allocations,
                "cost_delta_vs_optimal": check["cost_delta_vs_optimal"],
                "acknowledged_breaches": check["policy_breaches_acknowledged"],
            },
        )
        return to_response(run, db=db)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown HITL action '{body.action}'. Use approve, reject, or override.",
        )

