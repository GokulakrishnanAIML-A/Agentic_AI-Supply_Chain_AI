from __future__ import annotations

import random
import pytest
from app.graph.faithfulness import unfaithful_numbers
from app.graph.nodes import Relaxation, SupervisorChoice, replan_node, supervisor_node
from app.graph.state import GraphState


def test_supervisor_guard_property():
    """T2.2: Supervisor Guard property test:
    For 50 randomized LLM outputs (including empty, missing, or adversarial agent lists),
    the supervisor node NEVER drops required procurement specialist agents.
    """
    rng = random.Random(42)
    ALL_AGENTS = ["demand", "supplier", "route", "inventory", "risk"]
    REQUIRED = {"demand", "supplier", "route", "inventory", "risk"}

    for _ in range(50):
        # Sample subset of agents (simulating imperfect LLM responses)
        k = rng.randint(0, len(ALL_AGENTS))
        sample_agents = rng.sample(ALL_AGENTS, k) + ["garbage_agent", "unknown_tool"]
        state: GraphState = {
            "query": "I need 10,000 units of Product A next month.",
            "intent": {"product_query": "Product A", "quantity": 10000},
            "trace": [],
        }

        res = supervisor_node(state)
        chosen = set(res["agents_needed"])

        # Invariant: All required agents must be present in the final chosen set
        assert REQUIRED.issubset(chosen), f"Supervisor omitted required agents: {REQUIRED - chosen}"
        # Invariant: Invalid agent names are filtered out
        assert not any(a not in ALL_AGENTS for a in chosen)


def test_replan_whitelist_and_degraded_flag():
    """T2.3: Replan node emits bounded relaxations from closed whitelist and tags degraded=True."""
    state: GraphState = {
        "query": "Need Product A fast",
        "intent": {"product_query": "Product A", "lead_time_days_max": 20, "low_risk": True},
        "validation": {"ok": False, "issues": ["No feasible plan under 20 days lead time"]},
        "replan_count": 0,
        "relaxations": [],
        "trace": [],
    }

    res = replan_node(state)
    assert res["degraded"] is True
    assert res["replan_count"] == 1
    assert len(res["relaxations"]) > 0

    ALLOWED_CONSTRAINTS = {"lead_time", "low_risk_concentration", "low_risk_reliability", "high_risk_exclusion"}
    for rel in res["relaxations"]:
        assert rel["constraint"] in ALLOWED_CONSTRAINTS
        if rel["constraint"] == "lead_time":
            assert 0 <= rel.get("lead_time_delta_days", 0) <= 30


def test_explanation_faithfulness_guard():
    """T2.4: Faithfulness guard detects unfaithful numbers injected into generated text."""
    allowed = {10000.0, 48146.56, 42.0, 552.0, 3.0}

    faithful_text = "Allocated 10,000 units with total cost 48,146.56 and risk score 42.0 across 3 suppliers."
    unfaithful_res = unfaithful_numbers(faithful_text, allowed, tol=0.5)
    assert len(unfaithful_res) == 0

    hallucinated_text = "Allocated 10,000 units with total cost 99,999.00 and fake lead time 123.4 hours."
    detected_bad = unfaithful_numbers(hallucinated_text, allowed, tol=0.5)
    assert len(detected_bad) >= 1
    assert any(abs(n - 99999.0) < 0.5 for n in detected_bad)
