from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.schemas import AgentBundle, RouteOption, SupplierOffer
from app.core.config import settings


class Allocation(BaseModel):
    supplier_code: str
    supplier_name: str
    warehouse_code: str
    route_code: str
    mode: str
    quantity: int
    unit_price: float
    transport_cost_per_unit: float
    line_cost: float
    lead_time_days: int
    transit_hours: float
    reliability_score: float


class SolverResult(BaseModel):
    status: str
    total_cost: float
    procurement_cost: float
    transport_cost: float
    risk_penalty_cost: float
    delivery_time_hours: float
    allocations: list[Allocation] = Field(default_factory=list)
    unmet_demand: int = 0
    objective_notes: list[str] = Field(default_factory=list)
    infeasibility: str | None = None


def _solver():
    from ortools.linear_solver import pywraplp

    for name in ("CBC_MIXED_INTEGER_PROGRAMMING", "SCIP", "CBC", "SAT"):
        try:
            s = pywraplp.Solver.CreateSolver(name)
            if s:
                return s, name
        except Exception:
            continue
    s = pywraplp.Solver.CreateSolver("GLOP")
    return s, "GLOP"


def solve_bundle(
    bundle: AgentBundle,
    risk_weight: float | None = None,
    enforce_low_risk: bool = True,
) -> SolverResult:
    """MILP: quantities are decision variables. LLM does not compute them."""
    from ortools.linear_solver import pywraplp

    risk_weight = settings.risk_penalty_weight if risk_weight is None else risk_weight
    solver, backend = _solver()
    if solver is None:
        return SolverResult(
            status="solver_unavailable",
            total_cost=0,
            procurement_cost=0,
            transport_cost=0,
            risk_penalty_cost=0,
            delivery_time_hours=0,
            infeasibility="OR-Tools solver could not be created",
        )

    offers = {o.supplier_id: o for o in bundle.suppliers.offers if o.eligible}
    lanes: list[tuple[SupplierOffer, RouteOption]] = []
    for route in bundle.routes.routes:
        offer = offers.get(route.supplier_id)
        if not offer:
            continue
        if route.capacity_units <= 0:
            continue
        lanes.append((offer, route))

    demand = bundle.inventory.net_requirement
    if demand <= 0:
        return SolverResult(
            status="OPTIMAL",
            total_cost=0,
            procurement_cost=0,
            transport_cost=0,
            risk_penalty_cost=0,
            delivery_time_hours=0,
            objective_notes=["Net requirement is 0; inventory covers demand plus safety stock."],
        )

    if not lanes:
        return SolverResult(
            status="INFEASIBLE",
            total_cost=0,
            procurement_cost=0,
            transport_cost=0,
            risk_penalty_cost=0,
            delivery_time_hours=0,
            unmet_demand=demand,
            infeasibility="No eligible supplier-route lanes",
        )

    integer = backend != "GLOP"
    x = {}
    for offer, route in lanes:
        name = f"x_{offer.supplier_code}_{route.code}"
        ub = min(offer.monthly_capacity, route.capacity_units, demand + offer.moq)
        if integer:
            x[(offer.supplier_id, route.route_id)] = solver.IntVar(0, ub, name)
        else:
            x[(offer.supplier_id, route.route_id)] = solver.NumVar(0, ub, name)

    # Supplier capacity + MOQ
    y = {}
    for sid, offer in offers.items():
        related = [var for (s, r), var in x.items() if s == sid]
        if not related:
            continue
        total = solver.Sum(related)
        solver.Add(total <= offer.monthly_capacity)
        if integer:
            y[sid] = solver.BoolVar(f"use_{offer.supplier_code}")
            solver.Add(total <= offer.monthly_capacity * y[sid])
            solver.Add(total >= offer.moq * y[sid])

    # Warehouse remaining capacity
    incoming = {}
    for (sid, rid), var in x.items():
        route = next(r for o, r in lanes if r.route_id == rid)
        incoming.setdefault(route.warehouse_id, [])
        incoming[route.warehouse_id].append(var)
    inv_by_wh = {row.warehouse_id: row for row in bundle.inventory.rows}
    for wh_id, vars_ in incoming.items():
        inv = inv_by_wh.get(wh_id)
        if not inv:
            continue
        remaining = max(0, inv.capacity_units - inv.on_hand)
        solver.Add(solver.Sum(vars_) <= remaining)

    # Route capacity constraints
    by_route: dict[int, list] = {}
    for (sid, rid), var in x.items():
        by_route.setdefault(rid, []).append(var)
    for o, r in lanes:
        if r.route_id in by_route:
            solver.Add(solver.Sum(by_route[r.route_id]) <= r.capacity_units)

    solver.Add(solver.Sum(x.values()) >= demand)

    if enforce_low_risk and integer:
        total = solver.Sum(x.values())
        weighted_rel = solver.Sum(
            var * next(o.reliability_score for o, r in lanes if r.route_id == rid)
            for (sid, rid), var in x.items()
        )
        solver.Add(weighted_rel >= 0.90 * total)
        high_vars = [
            var
            for (sid, rid), var in x.items()
            if offers[sid].risk_tier == "high"
        ]
        if high_vars:
            solver.Add(solver.Sum(high_vars) <= 0.15 * total)
        for sid, offer in offers.items():
            related = [var for (s, r), var in x.items() if s == sid]
            if related:
                solver.Add(solver.Sum(related) <= 0.60 * total)

    obj_terms = []
    for (sid, rid), var in x.items():
        offer = offers[sid]
        route = next(r for o, r in lanes if r.route_id == rid)
        inv = inv_by_wh.get(route.warehouse_id)
        hold = (inv.holding_cost_per_unit if inv else 0.1) * 0.25
        penalty = risk_weight * (1 - offer.reliability_score) * offer.unit_price
        unit = offer.unit_price + route.effective_cost_per_unit + hold + penalty
        obj_terms.append(unit * var)

    solver.Minimize(solver.Sum(obj_terms))
    solver.SetTimeLimit(15_000)
    result = solver.Solve()

    status_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    status = status_map.get(result, str(result))

    if status not in {"OPTIMAL", "FEASIBLE"}:
        # Relax low-risk concentration constraints and retry once.
        if enforce_low_risk:
            return solve_bundle(bundle, risk_weight=risk_weight, enforce_low_risk=False)
        return SolverResult(
            status=status,
            total_cost=0,
            procurement_cost=0,
            transport_cost=0,
            risk_penalty_cost=0,
            delivery_time_hours=0,
            unmet_demand=demand,
            infeasibility="Solver could not find a feasible allocation",
            objective_notes=[f"backend={backend}"],
        )

    allocations: list[Allocation] = []
    proc = trans = pen = 0.0
    max_hours = 0.0
    for (sid, rid), var in x.items():
        qty = int(round(var.solution_value()))
        if qty <= 0:
            continue
        offer = offers[sid]
        route = next(r for o, r in lanes if r.route_id == rid)
        line_proc = qty * offer.unit_price
        line_tr = qty * route.effective_cost_per_unit
        line_pen = qty * risk_weight * (1 - offer.reliability_score) * offer.unit_price
        proc += line_proc
        trans += line_tr
        pen += line_pen
        hours = offer.lead_time_days * 24 + route.transit_hours
        max_hours = max(max_hours, hours)
        allocations.append(
            Allocation(
                supplier_code=offer.supplier_code,
                supplier_name=offer.supplier_name,
                warehouse_code=route.warehouse_code,
                route_code=route.code,
                mode=route.mode,
                quantity=qty,
                unit_price=offer.unit_price,
                transport_cost_per_unit=route.effective_cost_per_unit,
                line_cost=round(line_proc + line_tr, 2),
                lead_time_days=offer.lead_time_days,
                transit_hours=route.transit_hours,
                reliability_score=offer.reliability_score,
            )
        )

    filled = sum(a.quantity for a in allocations)
    return SolverResult(
        status=status,
        total_cost=round(proc + trans, 2),
        procurement_cost=round(proc, 2),
        transport_cost=round(trans, 2),
        risk_penalty_cost=round(pen, 2),
        delivery_time_hours=round(max_hours, 1),
        allocations=sorted(allocations, key=lambda a: (-a.quantity, a.supplier_code)),
        unmet_demand=max(0, demand - filled),
        objective_notes=[
            f"OR-Tools backend={backend}",
            "Objective minimizes procurement + transport + holding + reliability penalty.",
            "Quantities are solver outputs, not LLM estimates.",
            f"Low-risk constraints enforced={enforce_low_risk}",
        ],
    )


def evaluate_plan(
    bundle_or_data: AgentBundle | dict,
    allocations_raw: list[dict] | list[Allocation],
    optimal_cost: float | None = None,
    risk_weight: float | None = None,
    acknowledge_policy_breach: bool = False,
) -> dict:
    """Evaluate an allocation plan against all solver constraints and cost functions.

    Returns:
      {
        "ok": bool,
        "violations": list[str],
        "policy_breaches_acknowledged": list[str],
        "total_cost": float,
        "procurement_cost": float,
        "transport_cost": float,
        "risk_penalty_cost": float,
        "delivery_time_hours": float,
        "plan_risk": float,
        "cost_delta_vs_optimal": float,
        "filled": int,
        "net_requirement": int,
      }
    """
    risk_weight = settings.risk_penalty_weight if risk_weight is None else risk_weight
    violations: list[str] = []
    policy_breaches: list[str] = []

    # Extract reference maps depending on whether bundle or dict is provided
    if isinstance(bundle_or_data, AgentBundle):
        offers = {o.supplier_code: o for o in bundle_or_data.suppliers.offers}
        routes = {r.code: r for r in bundle_or_data.routes.routes}
        routes_by_pair = {(r.supplier_code if hasattr(r, 'supplier_code') else '', r.warehouse_code): r for r in bundle_or_data.routes.routes}
        inv_map = {r.warehouse_code: r for r in bundle_or_data.inventory.rows}
        net_req = bundle_or_data.inventory.net_requirement
    else:
        # Dictionary structure (e.g. from result_json)
        sup_data = bundle_or_data.get("suppliers") or {}
        raw_offers = sup_data.get("offers") or []
        offers = {
            o.get("supplier_code"): type("OfferObj", (), o)()
            for o in raw_offers if o.get("supplier_code")
        }
        rt_data = bundle_or_data.get("routes") or {}
        raw_routes = rt_data.get("routes") if isinstance(rt_data, dict) else (rt_data if isinstance(rt_data, list) else [])
        routes = {
            (r.get("code") or r.get("route_code")): type("RouteObj", (), r)()
            for r in raw_routes if (r.get("code") or r.get("route_code"))
        }
        routes_by_pair = {
            (r.get("supplier_code", ""), r.get("warehouse_code", "")): type("RouteObj", (), r)()
            for r in raw_routes if (r.get("supplier_code") and r.get("warehouse_code"))
        }
        inv_data = bundle_or_data.get("inventory") or {}
        raw_inv = inv_data.get("rows") or []
        inv_map = {
            r.get("warehouse_code"): type("InvObj", (), r)()
            for r in raw_inv if r.get("warehouse_code")
        }
        net_req = int(inv_data.get("net_requirement") or 0)

    # Normalize allocations
    norm_allocs = []
    for a in allocations_raw:
        if isinstance(a, Allocation):
            sup_code = a.supplier_code
            wh_code = a.warehouse_code
            rt_code = a.route_code
            qty = a.quantity
            u_price = a.unit_price
            tr_cost = a.transport_cost_per_unit
            lead_days = a.lead_time_days
            tr_hours = a.transit_hours
            rel = a.reliability_score
        else:
            sup_code = a.get("supplier_code", "")
            wh_code = a.get("warehouse_code", "WH-CENTRAL")
            rt_code = a.get("route_code", "")
            qty = int(a.get("quantity") if a.get("quantity") is not None else a.get("units", 0))
            offer = offers.get(sup_code)
            route = routes.get(rt_code) or routes_by_pair.get((sup_code, wh_code))
            u_price = float(a.get("unit_price") or (getattr(offer, "unit_price", 0.0) if offer else 0.0))
            tr_cost = float(a.get("transport_cost_per_unit") or (getattr(route, "effective_cost_per_unit", getattr(route, "cost_per_unit", 0.0)) if route else 0.0))
            lead_days = int(a.get("lead_time_days") or (getattr(offer, "lead_time_days", 0) if offer else 0))
            tr_hours = float(a.get("transit_hours") or (getattr(route, "transit_hours", 0.0) if route else 0.0))
            rel = float(a.get("reliability_score") or (getattr(offer, "reliability_score", 0.85) if offer else 0.85))

        if qty > 0:
            norm_allocs.append({
                "supplier_code": sup_code,
                "warehouse_code": wh_code,
                "route_code": rt_code,
                "quantity": qty,
                "unit_price": u_price,
                "transport_cost_per_unit": tr_cost,
                "lead_time_days": lead_days,
                "transit_hours": tr_hours,
                "reliability_score": rel,
            })

    filled = sum(a["quantity"] for a in norm_allocs)

    # 1. Total demand fulfillment check
    if filled < net_req:
        violations.append(f"Allocation {filled} below net requirement {net_req}")

    # 2. Supplier capacity and MOQ check
    by_sup: dict[str, int] = {}
    for a in norm_allocs:
        by_sup[a["supplier_code"]] = by_sup.get(a["supplier_code"], 0) + a["quantity"]

    for sup_code, qty in by_sup.items():
        offer = offers.get(sup_code)
        if offer:
            cap = getattr(offer, "monthly_capacity", float("inf"))
            moq = getattr(offer, "moq", 1)
            if qty > cap:
                violations.append(f"{sup_code} allocated {qty} over capacity {cap}")
            if qty < moq:
                violations.append(f"{sup_code} allocated {qty} below minimum order quantity (MOQ) {moq}")
        else:
            violations.append(f"Unknown or ineligible supplier {sup_code}")

    # 3. Warehouse capacity check
    by_wh: dict[str, int] = {}
    for a in norm_allocs:
        by_wh[a["warehouse_code"]] = by_wh.get(a["warehouse_code"], 0) + a["quantity"]

    for wh_code, qty in by_wh.items():
        inv = inv_map.get(wh_code)
        if inv:
            cap = getattr(inv, "capacity_units", float("inf"))
            on_hand = getattr(inv, "on_hand", 0)
            remaining = max(0, cap - on_hand)
            if qty > remaining:
                violations.append(f"Warehouse {wh_code} allocated {qty} over remaining capacity {remaining}")

    # 4. Route capacity check
    by_rt: dict[str, int] = {}
    for a in norm_allocs:
        if a["route_code"]:
            by_rt[a["route_code"]] = by_rt.get(a["route_code"], 0) + a["quantity"]

    for rt_code, qty in by_rt.items():
        rt = routes.get(rt_code)
        if rt:
            cap = getattr(rt, "capacity_units", float("inf"))
            if qty > cap:
                violations.append(f"Route {rt_code} allocated {qty} over capacity {cap}")

    # 5. Policy / Concentration checks
    if filled > 0:
        for sup_code, qty in by_sup.items():
            if qty > 0.60 * filled:
                policy_breaches.append(
                    f"Supplier {sup_code} share {qty/filled:.1%} exceeds concentration policy limit of 60%"
                )
        high_risk_qty = sum(
            qty for sup_code, qty in by_sup.items()
            if getattr(offers.get(sup_code), "risk_tier", "medium") == "high"
        )
        if high_risk_qty > 0.15 * filled:
            policy_breaches.append(
                f"High-risk supplier allocation {high_risk_qty/filled:.1%} exceeds policy limit of 15%"
            )
        weighted_rel = sum(a["quantity"] * a["reliability_score"] for a in norm_allocs) / filled
        if weighted_rel < 0.90:
            policy_breaches.append(
                f"Average supplier reliability {weighted_rel:.1%} is below policy minimum 90%"
            )

    if policy_breaches:
        if acknowledge_policy_breach:
            # Acknowledged -> not a blocking violation
            pass
        else:
            violations.extend(policy_breaches)

    # 6. Cost calculations
    proc_cost = sum(a["quantity"] * a["unit_price"] for a in norm_allocs)
    trans_cost = sum(a["quantity"] * a["transport_cost_per_unit"] for a in norm_allocs)
    pen_cost = sum(
        a["quantity"] * risk_weight * (1.0 - a["reliability_score"]) * a["unit_price"]
        for a in norm_allocs
    )
    total_cost = round(proc_cost + trans_cost, 2)
    lead_time_hours = max(
        (a["lead_time_days"] * 24 + a["transit_hours"] for a in norm_allocs),
        default=0.0,
    )
    avg_plan_risk = round(1.0 - (sum(a["quantity"] * a["reliability_score"] for a in norm_allocs) / filled), 4) if filled > 0 else 0.0

    cost_delta = round(total_cost - optimal_cost, 2) if optimal_cost is not None else 0.0

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "policy_breaches_acknowledged": policy_breaches if acknowledge_policy_breach else [],
        "total_cost": total_cost,
        "procurement_cost": round(proc_cost, 2),
        "transport_cost": round(trans_cost, 2),
        "risk_penalty_cost": round(pen_cost, 2),
        "delivery_time_hours": round(lead_time_hours, 1),
        "plan_risk": avg_plan_risk,
        "cost_delta_vs_optimal": cost_delta,
        "filled": filled,
        "net_requirement": net_req,
    }

