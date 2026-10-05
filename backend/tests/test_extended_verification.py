import pytest
from app.agents.schemas import AgentBundle, DemandResult, InventoryResult, InventoryRow, RiskResult, RouteOption, RouteResult, SupplierOffer, SupplierResult
from app.llm.factory import parse_intent
from app.optimization.solver import solve_bundle
from app.rag.search import search
from app.validation.validator import validate_plan
from app.whatif.engine import WhatIfRequest, build_patch, diff_results
from tests.conftest import product_a_bundle


def test_zero_net_requirement():
    """When inventory is sufficient to meet all demand, solver should return 0 cost without purchases."""
    bundle = product_a_bundle(1000)
    bundle.inventory.net_requirement = 0
    res = solve_bundle(bundle)
    assert res.status == "OPTIMAL"
    assert res.total_cost == 0.0
    assert len(res.allocations) == 0
    assert "Net requirement is 0" in res.objective_notes[0]


def test_extreme_demand_infeasible():
    """When demand massively exceeds combined capacity of all suppliers, solver should report INFEASIBLE."""
    bundle = product_a_bundle(100_000)
    bundle.inventory.net_requirement = 100_000
    res = solve_bundle(bundle, enforce_low_risk=False)
    assert res.status in {"INFEASIBLE", "NOT_SOLVED"} or res.unmet_demand > 0


def test_all_whatif_scenarios_build():
    """Verify build_patch correctly sets parameters for all 6 scenario types."""
    scenarios = [
        ("demand_increase", 30, "demand_multiplier", 1.3),
        ("price_increase", 15, "price_multiplier", 1.15),
        ("fuel_increase", 40, "fuel_multiplier", 1.4),
        ("inventory_shortage", 60, "inventory_factor", 0.4),
    ]
    for sc, pct, attr, expected in scenarios:
        patch = build_patch(WhatIfRequest(scenario=sc, pct=pct))
        assert abs(getattr(patch, attr) - expected) < 1e-4

    patch_sup = build_patch(WhatIfRequest(scenario="supplier_failure", supplier_code="SUP-B"))
    assert "SUP-B" in patch_sup.failed_supplier_codes

    patch_rt = build_patch(WhatIfRequest(scenario="route_disruption", route_code="RT-A-ROT-OC"))
    assert "RT-A-ROT-OC" in patch_rt.disrupted_route_codes


def test_whatif_diff_results():
    """Verify baseline vs scenario delta calculations."""
    base = {"total_cost": 10000.0, "delivery_time_hours": 48.0, "risk_score": 30.0, "unmet_demand": 0}
    scen = {"total_cost": 12500.0, "delivery_time_hours": 72.0, "risk_score": 45.0, "unmet_demand": 500}
    diff = diff_results(base, scen)
    assert diff["total_cost"]["delta"] == 2500.0
    assert diff["delivery_time_hours"]["delta"] == 24.0
    assert diff["risk_score"]["delta"] == 15.0
    assert diff["unmet_demand"]["delta"] == 500.0


def test_natural_language_intent_variations():
    """Verify intent parser on multiple phrasing formats."""
    # Query with Product B and 5,000 units
    i1 = parse_intent("We need 5000 units of Product B by the end of next month")
    assert i1.product_query == "Product B"
    assert i1.quantity == 5000

    # Query with low risk phrasing
    i2 = parse_intent("Get 15000 units of Product A with minimal risk and high resilience")
    assert i2.product_query == "Product A"
    assert i2.quantity == 15000
    assert i2.low_risk is True

    # Query with fast objective
    i3 = parse_intent("Need 3,000 units of Product A fast")
    assert i3.product_query == "Product A"
    assert i3.quantity == 3000
    assert i3.objective == "min_time"


def test_validator_detects_capacity_overflow():
    """Validation engine flags allocations that exceed supplier limits."""
    bundle = product_a_bundle(10000)
    result = solve_bundle(bundle)
    assert result.status in {"OPTIMAL", "FEASIBLE"}

    from app.optimization.solver import Allocation
    tampered_allocations = list(result.allocations)
    tampered_allocations.append(
        Allocation(
            supplier_code="SUP-A",
            supplier_name="Apex Components",
            warehouse_code="WH-ROT",
            route_code="RT-A-ROT-OC",
            mode="ocean",
            quantity=999999,
            unit_price=10.0,
            transport_cost_per_unit=1.0,
            line_cost=10999990.0,
            lead_time_days=25,
            transit_hours=120.0,
            reliability_score=0.91,
        )
    )
    tampered_result = result.model_copy(update={"allocations": tampered_allocations})
    val = validate_plan(bundle, tampered_result)
    assert val["ok"] is False
    assert any("over capacity" in issue for issue in val["issues"])


def test_api_whatif_nonexistent_run_404(client):
    """Calling what-if with an invalid run ID should return 404."""
    res = client.post(
        "/api/v1/what-if",
        json={"run_id": 99999999, "scenario": "demand_increase", "pct": 20},
    )
    assert res.status_code == 404


def test_hitl_approval_workflow(client):
    """Verify Human-in-the-Loop approval updates validation metadata and agent trace."""
    decision = client.post(
        "/api/v1/decisions",
        json={"query": "I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk."},
    ).json()
    run_id = decision["run_id"]

    # Initially should be PENDING_REVIEW
    assert decision["validation"]["hitl_status"] == "PENDING_REVIEW"

    hitl_res = client.post(
        f"/api/v1/decisions/{run_id}/hitl",
        json={
            "action": "approve",
            "planner_name": "Chief Procurement Officer",
            "comments": "Audited and approved for PO creation.",
        },
    )
    assert hitl_res.status_code == 200
    body = hitl_res.json()
    assert body["validation"]["hitl_status"] == "APPROVED"
    assert body["validation"]["hitl_planner"] == "Chief Procurement Officer"
    assert any("HITL:" in t for t in body["agent_trace"])


def test_hitl_double_approval_blocked(client):
    """Verify that approving an already-approved run returns HTTP 409."""
    decision = client.post(
        "/api/v1/decisions",
        json={"query": "I need 10,000 units of Product A next month."},
    ).json()
    run_id = decision["run_id"]

    # First approval succeeds
    res1 = client.post(
        f"/api/v1/decisions/{run_id}/hitl",
        json={"action": "approve", "planner_name": "Planner 1", "comments": "OK"},
    )
    assert res1.status_code == 200

    # Second approval returns 409
    res2 = client.post(
        f"/api/v1/decisions/{run_id}/hitl",
        json={"action": "approve", "planner_name": "Planner 2", "comments": "Try again"},
    )
    assert res2.status_code == 409


def test_hitl_rejection_triggers_reoptimization(client):
    """Verify that rejecting a plan creates a new child run via re-optimization."""
    decision = client.post(
        "/api/v1/decisions",
        json={"query": "I need 10,000 units of Product A next month. Find the lowest-cost supply plan."},
    ).json()
    original_run_id = decision["run_id"]

    # Reject the plan
    reject_res = client.post(
        f"/api/v1/decisions/{original_run_id}/hitl",
        json={
            "action": "reject",
            "planner_name": "Risk Auditor",
            "comments": "Lead times too long — source from alternative vendors",
        },
    )
    assert reject_res.status_code == 200
    body = reject_res.json()

    # New run should have a different run_id (child of the rejected run)
    assert body["run_id"] != original_run_id
    assert body["validation"]["hitl_status"] == "PENDING_REVIEW"
    assert body["optimization_status"] in ("OPTIMAL", "FEASIBLE")


def test_hitl_override_validates_constraints(client):
    """Verify that override allocations are validated against capacity constraints."""
    decision = client.post(
        "/api/v1/decisions",
        json={"query": "I need 10,000 units of Product A next month."},
    ).json()
    run_id = decision["run_id"]

    # Override with invalid allocation (exceeds capacity) — should fail with 422
    invalid_override = client.post(
        f"/api/v1/decisions/{run_id}/hitl",
        json={
            "action": "override",
            "planner_name": "Override Tester",
            "comments": "Testing bad override",
            "override_allocations": [
                {"supplier_code": "SUP-A", "supplier_name": "Test", "units": 999999, "cost": 1.0}
            ],
        },
    )
    assert invalid_override.status_code == 422

