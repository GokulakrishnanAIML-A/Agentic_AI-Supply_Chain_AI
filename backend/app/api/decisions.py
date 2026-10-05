from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import DecisionRequest, DecisionResponse, HITLActionRequest
from app.api.service import execute_decision, to_response
from app.db.models import DecisionRun
from app.db.session import get_db
from app.validation.validator import validate_override_allocations

router = APIRouter()


@router.post("/decisions", response_model=DecisionResponse)
def create_decision(body: DecisionRequest, db: Session = Depends(get_db)):
    run = execute_decision(db, body.query)
    return to_response(run)


@router.get("/runs/{run_id}", response_model=DecisionResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(DecisionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return to_response(run)


@router.post("/decisions/{run_id}/hitl", response_model=DecisionResponse)
def hitl_validation(run_id: int, body: HITLActionRequest, db: Session = Depends(get_db)):
    """Human-in-the-Loop decision gate.

    Actions:
    - **approve**: Sign off on the plan — records planner identity and timestamp.
    - **reject**: Flag non-viable plan — triggers re-optimization linked via parent_run_id.
    - **override**: Manually adjust allocations — validates against capacity constraints
      before accepting.
    """
    run = db.get(DecisionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Decision run not found")

    # ── Prevent double-approval ──
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
        run.hitl_reviewed_by = body.planner_name
        run.hitl_reviewed_at = now
        run.hitl_comments = body.comments
        val["hitl_status"] = "APPROVED"
        val["hitl_planner"] = body.planner_name
        val["hitl_comments"] = body.comments
        trace.append(
            f"HITL: Plan APPROVED by '{body.planner_name}' — \"{body.comments}\""
        )

    # ── REJECT — trigger re-optimization ──
    elif body.action == "reject":
        run.hitl_status = "REJECTED"
        run.hitl_reviewed_by = body.planner_name
        run.hitl_reviewed_at = now
        run.hitl_comments = body.comments
        val["hitl_status"] = "REJECTED"
        val["hitl_planner"] = body.planner_name
        val["hitl_comments"] = body.comments
        trace.append(
            f"HITL: Plan REJECTED by '{body.planner_name}' — \"{body.comments}\". "
            "Re-optimization triggered."
        )
        result["validation"] = val
        result["trace"] = trace
        run.result_json = result
        db.commit()
        db.refresh(run)

        # Re-run pipeline with the same query, linked to the rejected run
        new_run = execute_decision(db, run.query, parent_id=run.id)
        return to_response(new_run, rejection_parent_id=run.id)

    # ── OVERRIDE — validate then accept ──
    elif body.action == "override":
        if not body.override_allocations:
            raise HTTPException(
                status_code=422,
                detail="override_allocations required for override action",
            )
        # Validate overrides against hard constraints
        check = validate_override_allocations(result, body.override_allocations)
        if not check["ok"]:
            raise HTTPException(
                status_code=422,
                detail=f"Override violates constraints: {check['issues']}",
            )
        run.hitl_status = "APPROVED_WITH_OVERRIDE"
        run.hitl_reviewed_by = body.planner_name
        run.hitl_reviewed_at = now
        rec = dict(result.get("recommendation") or {})
        rec["supplier_allocation"] = body.override_allocations
        # Calculate new total cost if cost values provided
        new_cost = sum(
            float(a.get("cost") or (float(a.get("units", 0)) * float(a.get("cost_per_unit", 0))))
            for a in body.override_allocations
        )
        if new_cost > 0:
            rec["total_cost"] = round(new_cost, 2)
        result["recommendation"] = rec
        result["supplier_allocation"] = body.override_allocations
        val["hitl_status"] = "APPROVED_WITH_OVERRIDE"
        val["hitl_planner"] = body.planner_name
        val["hitl_comments"] = body.comments
        trace.append(
            f"HITL: Allocations OVERRIDDEN by '{body.planner_name}' — "
            f"validated against capacity constraints. \"{body.comments}\""
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown HITL action '{body.action}'. Use approve, reject, or override.",
        )

    result["validation"] = val
    result["trace"] = trace
    run.result_json = result
    db.commit()
    db.refresh(run)
    return to_response(run)
