from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.demand import run_demand_agent
from app.agents.inventory import run_inventory_agent
from app.agents.risk import run_risk_agent
from app.agents.route import run_route_agent
from app.agents.schemas import (
    AgentBundle,
    DemandResult,
    InventoryResult,
    RiskResult,
    RouteResult,
    SupplierResult,
)
from app.agents.supplier import run_supplier_agent
from app.core.config import settings
from app.graph.state import GraphState
from app.llm.factory import Intent, parse_intent
from app.optimization.solver import solve_bundle
from app.rag.search import search
from app.validation.validator import validate_plan
from app.whatif.engine import WhatIfPatch


def _trace(state: GraphState, msg: str) -> list[str]:
    return list(state.get("trace") or []) + [msg]


def parse_node(state: GraphState) -> dict[str, Any]:
    intent = parse_intent(state["query"])
    return {
        "intent": intent.model_dump(),
        "replan_count": state.get("replan_count") or 0,
        "trace": _trace(state, f"parsed intent product={intent.product_query} qty={intent.quantity}"),
    }


def supervisor_node(state: GraphState) -> dict[str, Any]:
    """LLM-powered supervisor that reasons about which specialist agents
    are required for the current query.  Falls back to all-five when the
    LLM is unavailable or returns an unrecognisable response."""
    ALL_AGENTS = ["demand", "supplier", "route", "inventory", "risk"]
    intent = state.get("intent") or {}

    try:
        from app.llm.factory import get_llm
        llm = get_llm()
        prompt = (
            f"A user submitted this supply-chain planning request:\n"
            f"  Product: {intent.get('product_query', 'unknown')}\n"
            f"  Quantity: {intent.get('quantity', 'unspecified')}\n"
            f"  Objective: {intent.get('objective', 'min_cost')}\n"
            f"  Query: {state.get('query', '')}\n\n"
            f"Choose which specialist agents are needed from: {ALL_AGENTS}.\n"
            f"Return JSON: {{\"agents\": [\"demand\", ...], \"reasoning\": \"...\"}}"
        )
        result = llm.complete_json(
            "You are a supply-chain planning supervisor. "
            "Select only the agents genuinely needed.",
            prompt,
        )
        raw = result.get("agents", ALL_AGENTS)
        needed = [a for a in raw if a in ALL_AGENTS] or ALL_AGENTS
        reasoning = result.get("reasoning", "LLM-selected")
    except Exception:
        # Deterministic fallback
        q = (state.get("query") or "").lower()
        if "inventory" in q and "supplier" not in q and "route" not in q and "cost" not in q:
            needed = ["demand", "inventory", "risk"]
        else:
            needed = ALL_AGENTS
        reasoning = "fallback-keyword"

    return {
        "agents_needed": needed,
        "trace": _trace(state, f"supervisor selected {needed} ({reasoning})"),
    }


def rag_node(db: Session, state: GraphState) -> dict[str, Any]:
    """Agentic RAG: uses the LLM to expand the user query into domain-
    specific search terms, then runs hybrid dense+sparse retrieval.
    Falls back to template expansion when the LLM is unavailable."""
    intent = Intent.model_validate(state["intent"])

    try:
        from app.llm.factory import get_llm
        llm = get_llm()
        result = llm.complete_json(
            "You are a supply-chain knowledge retrieval specialist. "
            "Generate an expanded search query that targets corporate "
            "sourcing policies, safety stock guidelines, and disruption "
            "playbooks relevant to the user's request.",
            f"User query: {state['query']}\n"
            f"Product: {intent.product_query}\n"
            f"Objective: {intent.objective}\n\n"
            f'Return JSON: {{"expanded_query": "...", "reasoning": "..."}}',
        )
        query = result.get("expanded_query", "")
        expansion_method = "llm"
    except Exception:
        query = ""
        expansion_method = "template"

    if not query.strip():
        # Template fallback
        query = (
            f"{state['query']} {intent.product_query} sourcing policy safety stock "
            f"disruption risk fuel"
        )
        expansion_method = "template"

    hits = search(db, query, k=6)
    return {
        "evidence": [h.model_dump() for h in hits],
        "trace": _trace(
            state,
            f"rag retrieved {len(hits)} chunks (expansion={expansion_method})",
        ),
    }


def _patch(state: GraphState) -> WhatIfPatch:
    raw = state.get("patch") or {}
    return WhatIfPatch.model_validate(raw) if raw else WhatIfPatch()


def specialists_node(db: Session, state: GraphState) -> dict[str, Any]:
    intent = Intent.model_validate(state["intent"])
    patch = _patch(state)
    demand = run_demand_agent(db, intent)
    if patch.demand_multiplier != 1.0:
        demand.demand_to_meet = int(round(demand.demand_to_meet * patch.demand_multiplier))
        demand.notes.append(f"What-if demand multiplier {patch.demand_multiplier}")
    suppliers = run_supplier_agent(
        db,
        intent,
        demand,
        failed_supplier_codes=set(patch.failed_supplier_codes),
        price_multiplier=patch.price_multiplier,
    )
    routes = run_route_agent(
        db,
        suppliers,
        disrupted_route_codes=set(patch.disrupted_route_codes),
        fuel_multiplier=patch.fuel_multiplier,
    )
    inventory = run_inventory_agent(db, demand, inventory_factor=patch.inventory_factor)
    risk = run_risk_agent(db, suppliers, routes)
    needed = set(state.get("agents_needed") or ["demand", "supplier", "route", "inventory", "risk"])
    return {
        "demand": demand.model_dump(),
        "suppliers": suppliers.model_dump(),
        "routes": routes.model_dump(),
        "inventory": inventory.model_dump(),
        "risk": risk.model_dump(),
        "trace": _trace(state, f"specialist agents completed ({sorted(needed)})"),
    }


def solve_node(state: GraphState) -> dict[str, Any]:
    bundle = AgentBundle(
        demand=DemandResult.model_validate(state["demand"]),
        suppliers=SupplierResult.model_validate(state["suppliers"]),
        routes=RouteResult.model_validate(state["routes"]),
        inventory=InventoryResult.model_validate(state["inventory"]),
        risk=RiskResult.model_validate(state["risk"]),
    )
    intent = Intent.model_validate(state["intent"])
    result = solve_bundle(bundle, enforce_low_risk=intent.low_risk)
    return {
        "solver": result.model_dump(),
        "trace": _trace(state, f"solver status={result.status} cost={result.total_cost}"),
    }


def validate_node(state: GraphState) -> dict[str, Any]:
    bundle = AgentBundle(
        demand=DemandResult.model_validate(state["demand"]),
        suppliers=SupplierResult.model_validate(state["suppliers"]),
        routes=RouteResult.model_validate(state["routes"]),
        inventory=InventoryResult.model_validate(state["inventory"]),
        risk=RiskResult.model_validate(state["risk"]),
        evidence=state.get("evidence") or [],
    )
    from app.optimization.solver import SolverResult

    solver = SolverResult.model_validate(state["solver"])
    report = validate_plan(bundle, solver)
    return {"validation": report, "trace": _trace(state, f"validation ok={report['ok']}")}


def should_replan(state: GraphState) -> str:
    report = state.get("validation") or {}
    count = int(state.get("replan_count") or 0)
    if not report.get("ok") and count < settings.max_replan:
        return "replan"
    return "explain"


def replan_node(state: GraphState) -> dict[str, Any]:
    """LLM-reflective replanning: analyses *why* the previous plan failed
    and decides which constraints to relax, rather than blindly adding
    +15 days and disabling risk controls every time."""
    validation = state.get("validation") or {}
    issues = validation.get("issues", [])
    intent = dict(state.get("intent") or {})
    old_lead = int(intent.get("lead_time_days_max") or 31)
    old_risk = intent.get("low_risk", True)

    try:
        from app.llm.factory import get_llm
        llm = get_llm()
        result = llm.complete_json(
            "You are a supply-chain planning expert analysing a failed "
            "optimisation run. Suggest targeted constraint changes.",
            f"The plan failed with these issues: {issues}\n"
            f"Current constraints: lead_time_days_max={old_lead}, "
            f"low_risk={old_risk}\n\n"
            f"Return JSON: {{\"lead_time_days_max\": N, "
            f"\"low_risk\": bool, \"reasoning\": \"...\"}}",
        )
        intent["lead_time_days_max"] = int(
            result.get("lead_time_days_max", old_lead + 15)
        )
        intent["low_risk"] = bool(result.get("low_risk", False))
        reasoning = result.get("reasoning", "LLM-guided relaxation")
    except Exception:
        # Deterministic fallback — original behaviour
        intent["lead_time_days_max"] = old_lead + 15
        intent["low_risk"] = False
        reasoning = "fallback: +15 days, low-risk disabled"

    return {
        "intent": intent,
        "replan_count": int(state.get("replan_count") or 0) + 1,
        "trace": _trace(state, f"replan: {reasoning}"),
    }


def explain_node(state: GraphState) -> dict[str, Any]:
    demand = state.get("demand") or {}
    solver = state.get("solver") or {}
    risk = state.get("risk") or {}
    inv = state.get("inventory") or {}
    allocs = solver.get("allocations") or []
    by_sup: dict[str, dict[str, Any]] = {}
    for a in allocs:
        rec = by_sup.setdefault(
            a["supplier_code"],
            {"supplier_code": a["supplier_code"], "supplier_name": a["supplier_name"], "units": 0, "cost": 0.0},
        )
        rec["units"] += a["quantity"]
        rec["cost"] += a["line_cost"]

    lines = [
        f"Demand to meet: {demand.get('demand_to_meet')} units of {demand.get('product_name')} "
        f"(forecast {demand.get('forecast_units')} via {demand.get('forecast_method')}).",
        f"Net procurement after inventory: {inv.get('net_requirement')} units.",
        f"Solver {solver.get('status')} with total cost {solver.get('total_cost')} "
        f"(procurement {solver.get('procurement_cost')} + transport {solver.get('transport_cost')}).",
        f"Longest fulfillment time {solver.get('delivery_time_hours')} hours. "
        f"Composite risk score {risk.get('score')}.",
    ]
    for rec in by_sup.values():
        lines.append(f"{rec['supplier_code']} ({rec['supplier_name']}) → {rec['units']} units.")
    if allocs:
        top_routes = sorted(allocs, key=lambda a: -a["quantity"])[:4]
        lines.append(
            "Best routes: "
            + "; ".join(f"{a['route_code']} {a['mode']} → {a['warehouse_code']} ({a['quantity']})" for a in top_routes)
        )
    evidence = state.get("evidence") or []
    if evidence:
        lines.append("Evidence used: " + "; ".join(e.get("title", "") for e in evidence[:4]))
    lines.append(
        "Reason: allocation quantities come from the OR-Tools model using database prices, "
        "capacities, lead times and route costs. The LLM only parsed the request and wrote this explanation."
    )
    rec = {
        "summary": " ".join(lines[:3]),
        "reason": "\n".join(lines),
        "supplier_allocation": list(by_sup.values()),
        "routes": allocs,
        "forecast_units": demand.get("forecast_units"),
        "demand_to_meet": demand.get("demand_to_meet"),
        "net_requirement": inv.get("net_requirement"),
        "total_cost": solver.get("total_cost"),
        "delivery_time_hours": solver.get("delivery_time_hours"),
        "risk_score": risk.get("score"),
        "optimization_status": solver.get("status"),
        "data_disclaimer": "SYNTHETIC DATA — demo only. Separate sources: database facts, forecast model, agent eligibility, solver quantities.",
    }
    return {"recommendation": rec, "trace": _trace(state, "explanation composed")}
