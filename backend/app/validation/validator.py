from __future__ import annotations

from app.agents.schemas import AgentBundle
from app.optimization.solver import SolverResult


def validate_plan(bundle: AgentBundle, solver: SolverResult) -> dict:
    issues: list[str] = []
    ok = True
    filled = sum(a.quantity for a in solver.allocations)
    if solver.status in {"OPTIMAL", "FEASIBLE"}:
        if filled + 1 < bundle.inventory.net_requirement:
            ok = False
            issues.append(
                f"Allocation {filled} below net requirement {bundle.inventory.net_requirement}"
            )
        by_sup: dict[str, int] = {}
        cap = {o.supplier_code: o.monthly_capacity for o in bundle.suppliers.offers}
        for a in solver.allocations:
            by_sup[a.supplier_code] = by_sup.get(a.supplier_code, 0) + a.quantity
        for code, qty in by_sup.items():
            if qty > cap.get(code, 0):
                ok = False
                issues.append(f"{code} allocated {qty} over capacity {cap.get(code)}")
        if not bundle.evidence:
            issues.append("No RAG evidence attached (non-blocking)")
    else:
        ok = False
        issues.append(solver.infeasibility or solver.status)

    return {
        "ok": ok,
        "issues": issues,
        "filled": filled,
        "net_requirement": bundle.inventory.net_requirement,
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
