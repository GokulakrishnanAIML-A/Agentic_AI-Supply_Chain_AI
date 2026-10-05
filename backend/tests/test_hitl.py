from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import current_planner
from app.api.schemas import DecisionRequest, HITLActionRequest, RejectReason
from app.api.service import execute_decision, persist_run, to_response
from app.core.config import settings
from app.db.base import Base
from app.db.models import DecisionEvent, DecisionRun
from app.db.repositories import append_event, get_events_for_run
from app.main import app
from app.optimization.solver import evaluate_plan
from app.validation.validator import validate_override_allocations


# ── SQLite In-Memory Database for Fast Deterministic Isolation ──
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    DecisionRun.__table__.create(bind=engine)
    DecisionEvent.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()



@pytest.fixture
def sample_run(test_db):
    state = {
        "intent": {"product": "Product A", "quantity": 5000},
        "demand": {"forecast_units": 5000, "demand_to_meet": 5000},
        "suppliers": {
            "offers": [
                {
                    "supplier_code": "SUP-A",
                    "supplier_name": "Supplier Alpha",
                    "monthly_capacity": 6000,
                    "moq": 500,
                    "unit_price": 10.0,
                    "lead_time_days": 5,
                    "reliability_score": 0.95,
                    "risk_tier": "low",
                },
                {
                    "supplier_code": "SUP-B",
                    "supplier_name": "Supplier Beta",
                    "monthly_capacity": 4000,
                    "moq": 1000,
                    "unit_price": 12.0,
                    "lead_time_days": 7,
                    "reliability_score": 0.92,
                    "risk_tier": "low",
                },
                {
                    "supplier_code": "SUP-C",
                    "supplier_name": "Supplier Gamma",
                    "monthly_capacity": 5000,
                    "moq": 200,
                    "unit_price": 15.0,
                    "lead_time_days": 10,
                    "reliability_score": 0.70,
                    "risk_tier": "high",
                },
            ]
        },
        "routes": {
            "routes": [
                {
                    "code": "R-A1",
                    "supplier_code": "SUP-A",
                    "warehouse_code": "WH-CENTRAL",
                    "mode": "truck",
                    "cost_per_unit": 2.0,
                    "capacity_units": 8000,
                    "transit_hours": 24.0,
                },
                {
                    "code": "R-B1",
                    "supplier_code": "SUP-B",
                    "warehouse_code": "WH-CENTRAL",
                    "mode": "truck",
                    "cost_per_unit": 3.0,
                    "capacity_units": 5000,
                    "transit_hours": 30.0,
                },
                {
                    "code": "R-C1",
                    "supplier_code": "SUP-C",
                    "warehouse_code": "WH-CENTRAL",
                    "mode": "air",
                    "cost_per_unit": 5.0,
                    "capacity_units": 5000,
                    "transit_hours": 12.0,
                },
            ]
        },
        "inventory": {
            "net_requirement": 5000,
            "rows": [
                {
                    "warehouse_code": "WH-CENTRAL",
                    "capacity_units": 10000,
                    "on_hand": 2000,
                    "holding_cost_per_unit": 0.5,
                }
            ],
        },
        "solver": {
            "status": "OPTIMAL",
            "total_cost": 60000.0,
            "allocations": [
                {
                    "supplier_code": "SUP-A",
                    "supplier_name": "Supplier Alpha",
                    "warehouse_code": "WH-CENTRAL",
                    "route_code": "R-A1",
                    "mode": "truck",
                    "quantity": 5000,
                    "unit_price": 10.0,
                    "transport_cost_per_unit": 2.0,
                    "line_cost": 60000.0,
                    "lead_time_days": 5,
                    "transit_hours": 24.0,
                    "reliability_score": 0.95,
                }
            ],
        },
        "recommendation": {
            "summary": "Allocate 5000 units to SUP-A",
            "supplier_allocation": [
                {
                    "supplier_code": "SUP-A",
                    "supplier_name": "Supplier Alpha",
                    "units": 5000,
                    "cost": 60000.0,
                }
            ],
            "execution_steps": ["Issue PO-101 to SUP-A for 5000 units"],
        },
    }
    run = persist_run(test_db, "I need 5000 units", state)
    return run


# ── T3.1 Tests: Append-Only Audit Log ──
def test_append_event_and_history(test_db, sample_run):
    events = get_events_for_run(test_db, sample_run.id)
    assert len(events) == 1
    assert events[0].action == "CREATED"
    assert events[0].actor == "system"

    # Append approve event
    ev2 = append_event(
        test_db,
        run_id=sample_run.id,
        actor="Alice",
        action="APPROVE",
        payload={"comment": "Approved Alpha"},
    )
    assert ev2.id is not None
    events_after = get_events_for_run(test_db, sample_run.id)
    assert len(events_after) == 2
    assert events_after[1].action == "APPROVE"
    assert events_after[1].actor == "Alice"


# ── T3.2 Tests: Authenticated Reviewer Identity ──
def test_current_planner_auth():
    # Valid key
    planner = current_planner("secret_key_123")
    assert planner == "lead_planner"

    planner_alice = current_planner("key_alice")
    assert planner_alice == "alice"

    # Missing key -> 401
    with pytest.raises(Exception) as exc:
        current_planner(None)
    assert exc.value.status_code == 401

    # Invalid key -> 401
    with pytest.raises(Exception) as exc:
        current_planner("invalid_secret")
    assert exc.value.status_code == 401


# ── T3.3 Tests: Meaningful Reject ──
def test_reject_comment_only(test_db, sample_run):
    from app.api.decisions import hitl_validation

    req = HITLActionRequest(
        action="reject",
        planner_name="Forged Name",
        comments="Budget suspended",
    )
    resp = hitl_validation(
        run_id=sample_run.id,
        body=req,
        reviewer="Bob",
        db=test_db,
    )
    assert sample_run.hitl_status == "REJECTED"
    assert sample_run.hitl_reviewed_by == "Bob"  # Identity from token, not body
    assert resp["run_id"] == sample_run.id

    events = get_events_for_run(test_db, sample_run.id)
    assert any(e.action == "REJECT" and e.actor == "Bob" for e in events)


# ── T3.4 Tests: Full-Fidelity Override & Invariants ──
def test_override_valid(test_db, sample_run):
    from app.api.decisions import hitl_validation

    req = HITLActionRequest(
        action="override",
        comments="Split between Alpha and Beta for resilience",
        override_allocations=[
            {"supplier_code": "SUP-A", "warehouse_code": "WH-CENTRAL", "units": 3000},
            {"supplier_code": "SUP-B", "warehouse_code": "WH-CENTRAL", "units": 2000},
        ],
        acknowledge_policy_breach=True,
    )
    resp = hitl_validation(
        run_id=sample_run.id,
        body=req,
        reviewer="Alice",
        db=test_db,
    )
    assert sample_run.hitl_status == "APPROVED_WITH_OVERRIDE"
    assert sample_run.hitl_reviewed_by == "Alice"
    assert resp["total_cost"] is not None
    # Delta vs optimal >= 0
    delta = resp["validation"]["cost_delta_vs_optimal"]
    assert delta >= 0


def test_override_moq_breach_rejected(sample_run):
    r_json = sample_run.result_json
    # SUP-B has MOQ = 1000, attempt allocation of 200 units
    allocations = [
        {"supplier_code": "SUP-A", "warehouse_code": "WH-CENTRAL", "units": 4800},
        {"supplier_code": "SUP-B", "warehouse_code": "WH-CENTRAL", "units": 200},
    ]
    check = validate_override_allocations(r_json, allocations)
    assert check["ok"] is False
    assert any("below minimum order quantity" in issue for issue in check["issues"])


def test_override_capacity_breach_rejected(sample_run):
    r_json = sample_run.result_json
    # SUP-B capacity is 4000, attempt allocation of 5000 units
    allocations = [
        {"supplier_code": "SUP-B", "warehouse_code": "WH-CENTRAL", "units": 5000},
    ]
    check = validate_override_allocations(r_json, allocations)
    assert check["ok"] is False
    assert any("over capacity" in issue for issue in check["issues"])


def test_override_concentration_breach_policy(sample_run):
    r_json = sample_run.result_json
    # Single supplier SUP-A gets 100% (5000/5000 > 60%)
    allocations = [
        {"supplier_code": "SUP-A", "warehouse_code": "WH-CENTRAL", "units": 5000},
    ]
    # Without acknowledge -> rejected
    check_no_ack = validate_override_allocations(r_json, allocations, acknowledge_policy_breach=False)
    assert check_no_ack["ok"] is False
    assert any("exceeds concentration policy" in issue for issue in check_no_ack["issues"])

    # With acknowledge -> accepted with logged breach
    check_ack = validate_override_allocations(r_json, allocations, acknowledge_policy_breach=True)
    assert check_ack["ok"] is True
    assert len(check_ack["policy_breaches_acknowledged"]) > 0


# ── T3.5 Tests: Recommendation Lock ──
def test_server_side_recommendation_lock(test_db, sample_run):
    # When pending review:
    resp = to_response(sample_run, db=test_db)
    assert resp["execution_locked"] is True
    assert "[LOCKED]" in resp["explainable_recommendation"]["execution_steps"][0]

    # After approval:
    sample_run.hitl_status = "APPROVED"
    sample_run.hitl_reviewed_by = "Alice"
    test_db.commit()

    resp_approved = to_response(sample_run, db=test_db)
    assert resp_approved["execution_locked"] is False
    assert resp_approved["explainable_recommendation"]["execution_status"] == "APPROVED_READY_FOR_EXECUTION"


# ── Double-approval conflict test ──
def test_double_approval_raises_409(test_db, sample_run):
    from app.api.decisions import hitl_validation

    req = HITLActionRequest(action="approve", comments="First approval")
    hitl_validation(run_id=sample_run.id, body=req, reviewer="Alice", db=test_db)

    # Attempt second approval
    with pytest.raises(Exception) as exc:
        hitl_validation(run_id=sample_run.id, body=req, reviewer="Bob", db=test_db)
    assert exc.value.status_code == 409
