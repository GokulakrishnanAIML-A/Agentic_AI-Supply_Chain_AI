# SupplyChainAI System Architecture & Governance Model

**SupplyChainAI** converts natural-language supply-chain requests into deterministic, explainable, and mathematically optimal procurement and rebalancing plans.

---

## 1. Architectural Philosophy: Neurosymbolic Decoupling

The fundamental principle governing SupplyChainAI is **strict neurosymbolic separation** (Rule R5):
- **Neural Layer (LLMs):** Responsible *exclusively* for semantic intent classification, domain query expansion, and natural-language synthesis.
- **Symbolic Layer (OR-Tools MILP & Python):** Responsible for *all* arithmetic calculations, safety stock evaluations, constraint checks, and linear cost optimizations.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                   Natural Language Query                    │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Intent Parsing Node     │
                        │  Regex / LLM with Pydantic│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH SUPERVISOR ORCHESTRATION                     │
│                                                                           │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌────────────────┐  │
│   │  Hybrid RAG Engine  │   │    Demand Agent     │   │ Supplier Agent │  │
│   │ Dense 768d + Sparse │   │  CV-tuned Forecast  │   │ MOQs & Capacity│  │
│   └─────────────────────┘   └─────────────────────┘   └────────────────┘  │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌────────────────┐  │
│   │     Route Agent     │   │   Inventory Agent   │   │   Risk Agent   │  │
│   │ Fuel & Disruption   │   │  Pure Net Req Calc  │   │ Split Risk Met │  │
│   └─────────────────────┘   └─────────────────────┘   └────────────────┘  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   OR-Tools MILP Solver    │
                        │ Linear Decision Variables │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │ Hard Invariant Validator  │
                        └─────────────┬─────────────┘
                                      │
                         ┌────────────┴────────────┐
             (Violations)│                         │(Feasible)
                         ▼                         │
          ┌──────────────────────────────┐         │
          │     Bounded Replan Node      │         │
          │ Closed Whitelist Relaxations │         │
          │   Emits `degraded: true`     │         │
          └──────────────┬───────────────┘         │
                         │                         │
                         └────────────┬────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │ Faithfulness Guard & Text │
                        │ Numeric hallucination drop│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   HITL Governance Engine  │
                        │ Append-only event log     │
                        │ Server recommendation lock│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   React Planner Console   │
                        └───────────────────────────┘
```

---

## 2. Multi-Agent Specialization & Data Flow

| Agent / Node | Primary Responsibility | Input Artifacts | Deterministic Output State |
|---|---|---|---|
| **Supervisor** | Enforces specialist DAG execution | `intent` | Guaranteed inclusion of `{supplier, route, inventory}` for procurement |
| **Hybrid RAG** | Policy grounding via dense kNN + FTS | Knowledge markdown | Top-k chunks with Reciprocal Rank Fusion (RRF) |
| **Demand Agent** | Statistical baseline estimation | 24-month order history | Blended naive + seasonal-3MA (MAPE: 6.49%) |
| **Supplier Agent** | Validates vendor capabilities | `supplier_products` | Capacity $Cap_s$, MOQ $MOQ_s$, base price, risk tiers |
| **Route Agent** | Logistics pathfinding & dynamic pricing | `routes`, active events | Effective transportation costs adjusted by fuel index |
| **Inventory Agent** | Stock availability & requirement | Warehouse balances | `net_requirement = max(0, D + SS - Avail)` |
| **Risk Agent** | Risk quantification & factor analysis | Weather, routes, suppliers | Decoupled `plan_risk` (0-100) vs `disruption_exposure` |

---

## 3. Mathematical Optimization Model (MILP)

Let $s \in S$ index suppliers, $r \in R$ index logistics routes, and $w \in W$ index destination distribution centers.

### Decision Variables:
- $x_{s,r} \in \mathbb{Z}_{\ge 0}$: Quantity of units procured from supplier $s$ shipped via route $r$.
- $y_s \in \{0, 1\}$: Binary activation variable indicating whether supplier $s$ is utilized.

### Objective Function:
$$\min \sum_{s,r} \Big( P_s + C_r \cdot F + H_w + \lambda \cdot (1 - \text{Rel}_s) \Big) \cdot x_{s,r}$$
Where $P_s$ is unit procurement price, $C_r$ is base transit cost, $F$ is dynamic marine fuel multiplier, $H_w$ is holding cost, and $\lambda$ is the risk penalty weight ($1.25$).

### Operational Constraints:
1. **Demand Satisfaction:**
   $$\sum_{s,r} x_{s,r} \ge \text{Net Requirement}$$
2. **Supplier Capacity & Minimum Order Quantity (MOQ):**
   $$\sum_r x_{s,r} \le \text{Cap}_s \cdot y_s \quad \forall s$$
   $$\sum_r x_{s,r} \ge \text{MOQ}_s \cdot y_s \quad \forall s$$
3. **Route Capacity & Disruption Closure:**
   $$\sum_s x_{s,r} \le \text{RouteCap}_r \quad \forall r \quad (\text{Disrupted} \implies \text{RouteCap}_r = 0)$$
4. **Warehouse Storage Inbound Capacity:**
   $$\sum_{(s,r) \to w} x_{s,r} \le \text{StorageCap}_w - \text{OnHand}_w \quad \forall w$$
5. **Low-Risk Policy Constraints (Optional):**
   - High-risk supplier exclusion: $y_s = 0$ for tier High.
   - Concentration limit: $\sum_r x_{s,r} \le 0.60 \cdot \sum_{s',r'} x_{s',r'}$.
   - Weighted reliability floor: $\sum_{s,r} \text{Rel}_s \cdot x_{s,r} \ge 0.70 \cdot \sum_{s,r} x_{s,r}$.

---

## 4. Invariant Validation & Bounded Re-Planning

1. **Shared Predicate Parity:** Both `backend/app/optimization/solver.py` and `backend/app/validation/validator.py` evaluate identical mathematical invariants.
2. **Bounded Replan Schema:** If initial conditions are infeasible, re-planning may apply up to `max_replan=2` rounds of explicit relaxations:
   - `lead_time`: Incremental window relaxation ($\le 30$ days).
   - `low_risk_concentration`: Relax maximum single-vendor share.
   - `low_risk_reliability`: Adjust reliability threshold.
   - `high_risk_exclusion`: Allow contingency high-risk tier.
3. **Transparency Invariant:** Whenever any relaxation is applied, the response explicitly tags `degraded: true` and includes structured `relaxations: [...]` with recorded justifications.

---

## 5. Human-in-the-Loop (HITL) Governance

1. **Append-Only Event Ledger:** Table `decision_events` logs all state transitions (`CREATED`, `APPROVE`, `REJECT`, `OVERRIDE`, `REPLAN`, `WHATIF`).
2. **Reviewer Identity Verification:** Planners provide authorization via `X-API-Key` headers; user identity is derived server-side.
3. **Server-Side Recommendation Lock:** The API redacts operational recommendations until state reaches `APPROVE` or `OVERRIDE`.
4. **Structured Rejection Lineage:** Rejections containing exclusion parameters trigger a modified child run linked by `parent_run_id`.
5. **Full-Fidelity Overrides:** Manual plans are evaluated against all linear constraints; cost delta relative to the optimal plan (`cost_delta_vs_optimal`) is displayed and stored.
