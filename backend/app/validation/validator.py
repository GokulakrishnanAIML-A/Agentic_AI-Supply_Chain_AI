from __future__ import annotations

from app.agents.schemas import AgentBundle
from app.optimization.solver import SolverResult, evaluate_plan



def validate_plan(bundle: AgentBundle, solver: SolverResult) -> dict:
    issues: list[str] = []
    ok = True
    filled = sum(a.quantity for a in solver.allocations)
    net_req = bundle.inventory.net_requirement

    if solver.status in {"OPTIMAL", "FEASIBLE"}:
        # 1. Demand fulfillment
        if filled < net_req:
            ok = False
            issues.append(
                f"Allocation {filled} below net requirement {net_req}"
            )

        # 2. Supplier capacity and MOQ
        by_sup: dict[str, int] = {}
        offer_map = {o.supplier_code: o for o in bundle.suppliers.offers}
        for a in solver.allocations:
            by_sup[a.supplier_code] = by_sup.get(a.supplier_code, 0) + a.quantity

        for code, qty in by_sup.items():
            offer = offer_map.get(code)
            if not offer:
                continue
            if qty > offer.monthly_capacity:
                ok = False
                issues.append(f"{code} allocated {qty} over capacity {offer.monthly_capacity}")
            if qty < offer.moq:
                ok = False
                issues.append(f"{code} allocated {qty} below minimum order quantity (MOQ) {offer.moq}")

        # 3. Warehouse inbound capacity
        by_wh: dict[str, int] = {}
        for a in solver.allocations:
            by_wh[a.warehouse_code] = by_wh.get(a.warehouse_code, 0) + a.quantity

        inv_map = {r.warehouse_code: r for r in bundle.inventory.rows}
        for wh_code, qty in by_wh.items():
            inv = inv_map.get(wh_code)
            if inv:
                remaining_space = max(0, inv.capacity_units - inv.on_hand)
                if qty > remaining_space:
                    ok = False
                    issues.append(f"Warehouse {wh_code} allocated {qty} over remaining capacity {remaining_space}")

        if not bundle.evidence:
            issues.append("No RAG evidence attached (non-blocking)")
    else:
        ok = False
        issues.append(solver.infeasibility or solver.status)

    overshoot = max(0, filled - net_req)
    return {
        "ok": ok,
        "issues": issues,
        "filled": filled,
        "net_requirement": net_req,
        "overshoot": overshoot,
    }


def validate_override_allocations(
    result_json: dict,
    override_allocations: list[dict],
    optimal_cost: float | None = None,
    acknowledge_policy_breach: bool = False,
) -> dict:
    """Validate human-override allocations using shared solver predicates and evaluate cost/risk."""
    eval_res = evaluate_plan(
        bundle_or_data=result_json,
        allocations_raw=override_allocations,
        optimal_cost=optimal_cost,
        acknowledge_policy_breach=acknowledge_policy_breach,
    )
    return {
        "ok": eval_res["ok"],
        "issues": eval_res["violations"],
        "violations": eval_res["violations"],
        "policy_breaches_acknowledged": eval_res["policy_breaches_acknowledged"],
        "total_cost": eval_res["total_cost"],
        "cost_delta_vs_optimal": eval_res["cost_delta_vs_optimal"],
        "delivery_time_hours": eval_res["delivery_time_hours"],
        "plan_risk": eval_res["plan_risk"],
        "evaluation": eval_res,
    }

