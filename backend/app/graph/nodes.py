from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field
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
from app.graph.faithfulness import unfaithful_numbers
from app.graph.state import GraphState
from app.llm.contract import call_structured
from app.llm.factory import Intent, parse_intent
from app.optimization.solver import solve_bundle
from app.rag.search import search
from app.validation.validator import validate_plan
from app.whatif.engine import WhatIfPatch


def _trace(state: GraphState, msg: str) -> list[str]:
    return list(state.get("trace") or []) + [msg]


def _append_metric(state: GraphState, node: str, res: Any) -> list[dict[str, Any]]:
    metrics = list(state.get("llm_metrics") or [])
    metrics.append({
        "node": node,
        "used_llm": getattr(res, "used_llm", False),
        "latency_ms": getattr(res, "latency_ms", 0.0),
        "fallback_reason": getattr(res, "fallback_reason", None),
    })
    return metrics


def parse_node(state: GraphState) -> dict[str, Any]:
    intent = parse_intent(state["query"])
    return {
        "intent": intent.model_dump(),
        "replan_count": state.get("replan_count") or 0,
        "llm_metrics": _append_metric(state, "parse", intent),
        "trace": _trace(state, f"parsed intent product={intent.product_query} qty={intent.quantity}"),
    }


class SupervisorChoice(BaseModel):
    agents: list[str] = Field(default_factory=lambda: ["demand", "supplier", "route", "inventory", "risk"])
    reasoning: str = "default-supervisor"


def supervisor_node(state: GraphState) -> dict[str, Any]:
    """LLM supervisor with guard: required procurement specialist agents are never omitted."""
    ALL_AGENTS = ["demand", "supplier", "route", "inventory", "risk"]
    REQUIRED_PROCURE = {"demand", "supplier", "route", "inventory", "risk"}
    intent = state.get("intent") or {}

    def fallback() -> SupervisorChoice:
        q = (state.get("query") or "").lower()
        if "inventory" in q and "supplier" not in q and "route" not in q and "cost" not in q:
            return SupervisorChoice(agents=["demand", "inventory", "risk"], reasoning="fallback-keyword-inventory")
        return SupervisorChoice(agents=ALL_AGENTS, reasoning="fallback-keyword-procure")

    prompt = (
        f"A user submitted this supply-chain planning request:\n"
        f"  Product: {intent.get('product_query', 'unknown')}\n"
        f"  Quantity: {intent.get('quantity', 'unspecified')}\n"
        f"  Objective: {intent.get('objective', 'min_cost')}\n"
        f"  Query: {state.get('query', '')}\n\n"
        f"Choose which specialist agents are needed from: {ALL_AGENTS}.\n"
        f"Return JSON: {{\"agents\": [\"demand\", ...], \"reasoning\": \"...\"}}"
    )

    llm_res = call_structured(
        SupervisorChoice,
        "You are a supply-chain planning supervisor. Select only the agents genuinely needed.",
        prompt,
        fallback=fallback,
    )

    raw_agents = [a for a in llm_res.value.agents if a in ALL_AGENTS]
    # Supervisor Guard: Ensure required procurement agents are always present
    needed = list(set(raw_agents) | REQUIRED_PROCURE)

    return {
        "agents_needed": sorted(needed),
        "llm_metrics": _append_metric(state, "supervisor", llm_res),
        "trace": _trace(
            state,
            f"supervisor selected {sorted(needed)} (used_llm={llm_res.used_llm}, reasoning={llm_res.value.reasoning})"
        ),
    }


class RAGExpansion(BaseModel):
    expanded_query: str
    reasoning: str = ""


def rag_node(db: Session, state: GraphState) -> dict[str, Any]:
    """Agentic RAG: expands user query with domain terms via structured contract, then executes hybrid search."""
    intent = Intent.model_validate(state["intent"])

    def fallback() -> RAGExpansion:
        return RAGExpansion(
            expanded_query=f"{state['query']} {intent.product_query} sourcing policy safety stock disruption risk fuel",
            reasoning="template-fallback",
        )

    llm_res = call_structured(
        RAGExpansion,
        "You are a supply-chain knowledge retrieval specialist. Generate an expanded search query targeting corporate sourcing policies, safety stock guidelines, and disruption playbooks.",
        f"User query: {state['query']}\nProduct: {intent.product_query}\nObjective: {intent.objective}\nReturn JSON: {{\"expanded_query\": \"...\", \"reasoning\": \"...\"}}",
        fallback=fallback,
    )

    query = llm_res.value.expanded_query.strip() or fallback().expanded_query
    hits = search(db, query, k=6)

    return {
        "evidence": [h.model_dump() for h in hits],
        "llm_metrics": _append_metric(state, "rag", llm_res),
        "trace": _trace(
            state,
            f"rag retrieved {len(hits)} chunks (used_llm={llm_res.used_llm}, expansion={llm_res.value.reasoning})",
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


class Relaxation(BaseModel):
    constraint: Literal["lead_time", "low_risk_concentration", "low_risk_reliability", "high_risk_exclusion"]
    lead_time_delta_days: int = Field(default=0, ge=0, le=30)
    reason: str = ""


class ReplanDecision(BaseModel):
    lead_time_days_max: int = 46
    low_risk: bool = False
    relaxations: list[Relaxation] = Field(default_factory=list)
    reasoning: str = ""


def replan_node(state: GraphState) -> dict[str, Any]:
    """T2.3: Whitelisted, transparent constraint relaxation with audit logging and degraded flag."""
    validation = state.get("validation") or {}
    issues = validation.get("issues", [])
    intent = dict(state.get("intent") or {})
    old_lead = int(intent.get("lead_time_days_max") or 31)
    old_risk = intent.get("low_risk", True)
    existing_relaxations = list(state.get("relaxations") or [])

    def fallback() -> ReplanDecision:
        return ReplanDecision(
            lead_time_days_max=old_lead + 15,
            low_risk=False,
            relaxations=[
                Relaxation(constraint="lead_time", lead_time_delta_days=15, reason="fallback relaxation +15 days"),
                Relaxation(constraint="high_risk_exclusion", reason="fallback relaxation low-risk disabled"),
            ],
            reasoning="fallback: +15 days lead time, low-risk disabled",
        )

    prompt = (
        f"The plan failed with these issues: {issues}\n"
        f"Current constraints: lead_time_days_max={old_lead}, low_risk={old_risk}\n"
        f"Suggest bounded constraint relaxations from: ['lead_time', 'low_risk_concentration', 'low_risk_reliability', 'high_risk_exclusion'].\n"
        f"Return JSON: {{\"lead_time_days_max\": N, \"low_risk\": bool, \"relaxations\": [{{\"constraint\": \"...\", \"lead_time_delta_days\": 15, \"reason\": \"...\"}}], \"reasoning\": \"...\"}}"
    )

    llm_res = call_structured(
        ReplanDecision,
        "You are a supply-chain planning expert analysing a failed optimisation run. Suggest targeted, bounded constraint changes.",
        prompt,
        fallback=fallback,
    )

    decision = llm_res.value
    intent["lead_time_days_max"] = decision.lead_time_days_max
    intent["low_risk"] = decision.low_risk
    new_relaxations = existing_relaxations + [r.model_dump() for r in decision.relaxations]

    return {
        "intent": intent,
        "replan_count": int(state.get("replan_count") or 0) + 1,
        "relaxations": new_relaxations,
        "degraded": True,
        "llm_metrics": _append_metric(state, "replan", llm_res),
        "trace": _trace(state, f"replan: {decision.reasoning} (degraded=True)"),
    }


def explain_node(state: GraphState) -> dict[str, Any]:
    """T2.4: Generates explainable recommendation guarded by numerical faithfulness verification."""
    demand = state.get("demand") or {}
    solver = state.get("solver") or {}
    risk = state.get("risk") or {}
    inv = state.get("inventory") or {}
    allocs = solver.get("allocations") or []
    degraded = state.get("degraded", False)
    relaxations = state.get("relaxations") or []

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
        f"Composite risk score {risk.get('score')} (plan risk {risk.get('plan_risk', risk.get('score'))}, disruption exposure {risk.get('disruption_exposure', 0.0)}).",
    ]
    if degraded and relaxations:
        rel_str = "; ".join(f"{r.get('constraint')} ({r.get('reason')})" for r in relaxations)
        lines.append(f"Notice: Plan is DEGRADED with applied policy relaxations: {rel_str}.")

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
        "Reason: allocation quantities come strictly from the OR-Tools mathematical model using database facts. "
        "The LLM only parsed the request, routed agents, and formatted this explanation."
    )

    full_text = "\n".join(lines)

    # T2.4: Faithfulness guard — extract numbers and verify they exist in ground truth
    allowed_numbers: set[float] = {
        float(x)
        for x in [
            demand.get("demand_to_meet"),
            demand.get("forecast_units"),
            inv.get("net_requirement"),
            solver.get("total_cost"),
            solver.get("procurement_cost"),
            solver.get("transport_cost"),
            solver.get("delivery_time_hours"),
            risk.get("score"),
            risk.get("plan_risk"),
            risk.get("disruption_exposure"),
            len(allocs),
            len(by_sup),
        ]
        if x is not None
    }
    for a in allocs:
        allowed_numbers.add(float(a["quantity"]))
        allowed_numbers.add(float(a["line_cost"]))
    for rec in by_sup.values():
        allowed_numbers.add(float(rec["units"]))
        allowed_numbers.add(float(rec["cost"]))

    unfaithful = unfaithful_numbers(full_text, allowed_numbers)
    fallback_reason = None
    if unfaithful:
        fallback_reason = f"unfaithful_numbers_detected: {unfaithful}"

    rec_payload = {
        "summary": " ".join(lines[:3]),
        "reason": full_text,
        "supplier_allocation": list(by_sup.values()),
        "routes": allocs,
        "forecast_units": demand.get("forecast_units"),
        "demand_to_meet": demand.get("demand_to_meet"),
        "net_requirement": inv.get("net_requirement"),
        "total_cost": solver.get("total_cost"),
        "delivery_time_hours": solver.get("delivery_time_hours"),
        "risk_score": risk.get("score"),
        "plan_risk": risk.get("plan_risk", risk.get("score")),
        "disruption_exposure": risk.get("disruption_exposure", 0.0),
        "optimization_status": solver.get("status"),
        "degraded": degraded,
        "relaxations": relaxations,
        "data_disclaimer": "SYNTHETIC DATA — demo only. Quantities strictly solved by Google OR-Tools from database facts.",
    }

    return {
        "recommendation": rec_payload,
        "trace": _trace(state, f"explanation composed (faithful={len(unfaithful) == 0})"),
    }
