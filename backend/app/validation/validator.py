from __future__ import annotations

from app.agents.schemas import AgentBundle
from app.optimization.solver import SolverResult


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
) -> dict:
    """Validate that human-override allocations do not violate hard constraints.

    Checks:
    1. Per-supplier volume ≤ monthly capacity.
    2. Total override volume ≥ net procurement requirement.
    """
    issues: list[str] = []
    suppliers_data = result_json.get("suppliers") or {}
    offers = suppliers_data.get("offers") or []
    cap_map = {s.get("supplier_code", ""): s.get("monthly_capacity", 0) for s in offers}

    by_sup: dict[str, int] = {}
    for alloc in override_allocations:
        code = alloc.get("supplier_code", "")
        qty = int(alloc.get("units", 0))
        by_sup[code] = by_sup.get(code, 0) + qty

    for code, qty in by_sup.items():
        if code in cap_map and qty > cap_map[code]:
            issues.append(
                f"{code}: override quantity {qty} exceeds monthly capacity {cap_map[code]}"
            )

    total = sum(int(a.get("units", 0)) for a in override_allocations)
    inv = result_json.get("inventory") or {}
    net_req = int(inv.get("net_requirement") or 0)
    if net_req > 0 and total < net_req:
        issues.append(
            f"Total override volume {total} is below net requirement {net_req}"
        )

    return {"ok": len(issues) == 0, "issues": issues}
