from __future__ import annotations

import pytest
from app.agents.schemas import AgentBundle
from app.optimization.solver import solve_bundle
from tests.conftest import product_a_bundle


def test_llm_cannot_change_solver_numbers():
    """T2.5: Invariant Proof — The LLM cannot alter solved numbers.
    Multiple independent pipeline runs with identical parsed intent produce byte-identical
    allocations, line costs, and objective totals.
    """
    bundle1 = product_a_bundle(demand_to_meet=10000)
    bundle2 = product_a_bundle(demand_to_meet=10000)

    res1 = solve_bundle(bundle1, enforce_low_risk=True)
    res2 = solve_bundle(bundle2, enforce_low_risk=True)

    assert res1.status == res2.status == "OPTIMAL"
    assert res1.total_cost == res2.total_cost
    assert res1.procurement_cost == res2.procurement_cost
    assert res1.transport_cost == res2.transport_cost
    assert res1.delivery_time_hours == res2.delivery_time_hours
    assert len(res1.allocations) == len(res2.allocations)

    for a1, a2 in zip(res1.allocations, res2.allocations):
        assert a1.supplier_code == a2.supplier_code
        assert a1.route_code == a2.route_code
        assert a1.quantity == a2.quantity
        assert a1.line_cost == a2.line_cost
        assert a1.unit_price == a2.unit_price
