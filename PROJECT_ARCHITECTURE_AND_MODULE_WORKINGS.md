# SupplyChainAI — Comprehensive System Architecture & Module Working Guide

## 1. Executive Summary & Core Philosophy

**SupplyChainAI** is a multi-agent decision intelligence platform for supply chain management. It converts natural-language operational problems (e.g., *"I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk."*) into mathematical, fully validated, and explainable sourcing and fulfillment plans.

### The Fundamental Separation Principle (Hard Architectural Rule)
> **The Language Model (LLM) NEVER chooses numerical order quantities, prices, or costs.**
> - **LLM Role**: Intent extraction, dynamic supervisor routing, semantic RAG query expansion, reflective replanning analysis, and synthesis of human-readable explanations.
> - **Mathematical Solvers (Google OR-Tools MILP)**: Computes optimal procurement and shipment quantities based strictly on database records, contractual constraints, route capacities, and lead times.
> - **Deterministic Heuristics / Statistical Models**: Computes historical demand forecasting (seasonal naive + moving averages), inventory availability, and risk indices.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER INTERACTION                                │
│           React 18 + Vite SPA  ◄──►  FastAPI REST API (/api/v1)             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATION PIPELINE                       │
│                                                                             │
│  [1. Parse Node]  ──► [2. Supervisor] ──► [3. Agentic RAG] ──► [4. Specialists]
│    (LLM Intent)       (Dynamic Route)    (Dense+Sparse RRF)   ├─ Demand Agent
│                                                               ├─ Supplier Agent
│                                                               ├─ Route Agent
│                                                               ├─ Inventory Agent
│                                                               └─ Risk Agent
│                                                                      │
│                                                                      ▼
│  [8. Explain Node] ◄── [7. Replan] ◄── [6. Validate] ◄── [5. Solve Node]    │
│    (Synthesis & Trace)  (LLM Reflect)   (Hard Checks)    (OR-Tools MILP)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATA & GOVERNANCE FOUNDATION                            │
│  • PostgreSQL + pgvector (Hybrid FTS + Dense Embeddings)                    │
│  • Human-in-the-Loop (HITL) Decision Gate (Approve / Reject / Override)     │
│  • What-If Scenario Stress-Testing Engine (Multipliers & Lineage)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Workspace Directory Structure

```
Agentic_AI-main/
├── backend/
│   ├── app/
│   │   ├── agents/               # 5 domain-specific specialist agents
│   │   │   ├── demand.py         # Statistical seasonal demand forecasting
│   │   │   ├── inventory.py      # DC availability & net requirement engine
│   │   │   ├── risk.py           # Multi-factor composite risk scoring rubric
│   │   │   ├── route.py          # Transportation lane feasibility & fuel factor
│   │   │   ├── schemas.py        # Pydantic schemas for agent payloads
│   │   │   └── supplier.py       # Sourcing eligibility, MOQ, lead-time checks
│   │   ├── api/                  # FastAPI endpoints & route controllers
│   │   │   ├── catalog.py        # Master catalog browsing endpoints
│   │   │   ├── decisions.py      # Decision planning, runs, and HITL gate
│   │   │   ├── health.py         # System health & dependency verification
│   │   │   ├── schemas.py        # Request/response contracts
│   │   │   ├── service.py        # Pipeline execution & state persistence
│   │   │   └── whatif.py         # What-If scenario simulation endpoint
│   │   ├── core/                 # Shared foundations
│   │   │   ├── config.py         # Pydantic Settings & environment variables
│   │   │   ├── logging.py        # Structured logging initialization
│   │   │   ├── paths.py          # Relative & absolute filesystem path resolution
│   │   │   └── provenance.py     # Provenance lineage & EvidenceHit models
│   │   ├── db/                   # Persistence layer
│   │   │   ├── base.py           # SQLAlchemy DeclarativeBase
│   │   │   ├── models.py         # 14 Relational & Vector database entities
│   │   │   ├── repositories.py   # Database query access layer
│   │   │   └── session.py        # Engine, SessionLocal, auto-migrations
│   │   ├── graph/                # LangGraph State Machine
│   │   │   ├── graph.py          # StateGraph assembly & conditional branches
│   │   │   ├── nodes.py          # Node implementations (parse, solve, replan, etc.)
│   │   │   └── state.py          # TypedDict GraphState definition
│   │   ├── llm/                  # LLM Client Abstractions
│   │   │   └── factory.py        # MockLLM (Regex fallback) & GeminiLLM (GenAI)
│   │   ├── optimization/         # Operations Research & Optimization
│   │   │   └── solver.py         # Google OR-Tools MILP formulation
│   │   ├── rag/                  # Retrieval-Augmented Generation
│   │   │   ├── embed.py          # Gemini text-embedding-004 & mock embedder
│   │   │   ├── ingest.py         # Markdown policy chunking & vector indexing
│   │   │   └── search.py         # Hybrid dense + sparse (tsvector) RRF retrieval
│   │   ├── validation/           # Business rule and integrity enforcement
│   │   │   └── validator.py      # Plan validation & HITL override checks
│   │   ├── whatif/               # Scenario simulation
│   │   │   └── engine.py         # Patch builder & baseline vs. scenario diff
│   │   └── main.py               # FastAPI app lifespan, CORS, route inclusion
│   ├── scripts/                  # Backend CLI utilities
│   │   ├── ingest_rag.py         # Standalone RAG ingestion script
│   │   ├── seed.py               # Deterministic synthetic data generator
│   │   └── seed_cli.py           # CLI invocation wrapper for database seed
│   ├── tests/                    # Pytest verification suite
│   │   ├── conftest.py           # Fixtures, test DB session, mock models
│   │   ├── test_api.py           # REST API endpoint unit & integration tests
│   │   ├── test_pipeline.py      # LangGraph end-to-end pipeline execution tests
│   │   └── test_extended_verification.py # Full 23-test regression suite
│   ├── Dockerfile                # Production container specification
│   ├── requirements.txt          # Python dependencies
│   └── pytest.ini                # Test runner configuration
├── frontend/                     # React 18 + TypeScript + Vite Dashboard
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts         # Typed API client for FastAPI endpoints
│   │   ├── App.tsx               # Main dashboard UI component
│   │   ├── index.css             # Vanilla CSS design system
│   │   └── main.tsx              # React DOM entrypoint
│   ├── package.json              # Frontend package definitions
│   └── vite.config.ts            # Vite build & proxy configuration
├── data/
│   ├── knowledge/                # Unstructured supply chain operational documents
│   │   ├── disruption_playbook.md
│   │   ├── fuel_surcharge_policy.md
│   │   ├── inventory_safety_stock.md
│   │   ├── product_a_brief.md
│   │   ├── risk_scoring.md
│   │   ├── supplier_sourcing_policy.md
│   │   └── transport_mode_guide.md
│   └── seed/                     # Pre-generated synthetic CSV datasets
│       ├── orders.csv
│       ├── products.csv
│       ├── routes.csv
│       ├── supplier_products.csv
│       ├── suppliers.csv
│       └── warehouses.csv
├── scripts/                      # Evaluation & benchmarking scripts
│   ├── benchmark_rag_ablation.py # Dense vs Sparse vs Hybrid retrieval ablation
│   └── evaluate_llms.py          # LLM intent parsing benchmark
├── docker-compose.yml            # Local development orchestration (Postgres + Backend + Frontend)
├── verify_system.py              # 5-step system verification script
└── PROJECT_STATUS.md             # Implementation milestone tracker
```

---

## 3. Database Schema & Data Models (`backend/app/db/models.py`)

The PostgreSQL database (accelerated with `pgvector`) persists relational facts, time-series data, document vector embeddings, and execution histories:

| Table Name | Entity Class | Primary Purpose & Key Fields |
|---|---|---|
| `products` | `Product` | Catalog of manufactured SKUs (`sku`, `name`, `category`, `unit`, `weight_kg`). |
| `suppliers` | `Supplier` | Global vendor registry with geographic coordinates, reliability rating, and baseline risk tier (`reliability_score`, `risk_tier`, `status`). |
| `supplier_products` | `SupplierProduct` | Sourcing contract terms: unit price, currency, monthly capacity, lead time in days, and minimum order quantity (MOQ). |
| `warehouses` | `Warehouse` | Destination fulfillment distribution centers (DCs) (`capacity_units`, location). |
| `inventory` | `Inventory` | Real-time stock levels per warehouse and product: `on_hand`, `reserved`, `safety_stock`, and `holding_cost_per_unit`. |
| `routes` | `Route` | Multimodal transportation lanes (Air, Ocean, Rail, Road) linking suppliers to warehouses (`distance_km`, `transit_hours`, `cost_per_unit`, `capacity_units`, `fuel_factor`, `status`). |
| `orders` | `Order` | Historical demand records used for statistical time-series forecasting. |
| `shipments` | `Shipment` | Historical transit logs tracking actual lead times and landed costs. |
| `risk_events` | `RiskEvent` | Active disruptions (`event_type`, `severity`, `affected_supplier_id`, `affected_route_id`, `status`). |
| `market_prices` | `MarketPrice` | Macroeconomic market indices such as the marine fuel index (`metric`, `value`, `observed_at`). |
| `weather_events` | `WeatherEvent` | Severe weather disruptions affecting geographic regions (`disruption_factor`). |
| `documents` | `Document` | Source unstructured operational policies and SOP playbooks. |
| `document_chunks` | `DocumentChunk` | Segmented text chunks storing `Vector(768)` embeddings alongside `TSVECTOR` for hybrid search. |
| `decision_runs` | `DecisionRun` | Immutable audit trail storing the complete input request, full state snapshot, parent-child lineages, and **HITL governance columns** (`hitl_status`, `hitl_reviewed_by`, `hitl_reviewed_at`, `hitl_comments`). |

---

## 4. Multi-Agent System Architecture

The core of SupplyChainAI is composed of specialized agents cooperating within a LangGraph state graph.

### 4.1. Specialist Agents Breakdown (`backend/app/agents/`)

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │                          SPECIALIST AGENTS                             │
   ├───────────────────────┬────────────────────────────────────────────────┤
   │ Agent                 │ Responsibility & Mechanism                     │
   ├───────────────────────┼────────────────────────────────────────────────┤
   │ Demand Agent          │ Computes 24-month historical order demand      │
   │ (demand.py)           │ using a 55/45 blend of Seasonal Naive and      │
   │                       │ Trailing 3-Month Moving Average.               │
   ├───────────────────────┼────────────────────────────────────────────────┤
   │ Supplier Agent        │ Evaluates vendor contract constraints from DB. │
   │ (supplier.py)         │ Filters active suppliers, checks MOQ, verifies │
   │                       │ max lead time, and tags risk penalties.        │
   ├───────────────────────┼────────────────────────────────────────────────┤
   │ Route Agent           │ Discovers feasible multimodal freight lanes.   │
   │ (route.py)            │ Checks route status, applies fuel surcharges,  │
   │                       │ and blocks lanes affected by active events.    │
   ├───────────────────────┼────────────────────────────────────────────────┤
   │ Inventory Agent       │ Calculates available stock (on_hand - reserved)│
   │ (inventory.py)        │ across DCs and determines net procurement:     │
   │                       │ net = demand_to_meet - available + safety_gap. │
   ├───────────────────────┼────────────────────────────────────────────────┤
   │ Risk Agent            │ Generates composite risk score (0-100) using a │
   │ (risk.py)             │ deterministic rubric: vendor reliability (40%),│
   │                       │ active disruptions (30%), weather (20%), fuel. │
   └───────────────────────┴────────────────────────────────────────────────┘
```

### 4.2. LangGraph State Machine Execution Flow (`backend/app/graph/`)

The workflow is orchestrated via `StateGraph(GraphState)` in `backend/app/graph/graph.py`:

```
   [START]
      │
      ▼
   [parse] ────────────► Uses LLM or regex to extract product, quantity, horizon, low_risk
      │
      ▼
 [supervisor] ─────────► Evaluates query to select which specialist agents are needed
      │
      ▼
    [rag] ─────────────► LLM expands search query; runs dense + sparse RRF against pgvector
      │
      ▼
 [specialists] ────────► Runs Demand, Supplier, Route, Inventory, and Risk agents
      │
      ▼
   [solve] ────────────► Formulates and executes Google OR-Tools MILP optimization
      │
      ▼
  [validate] ──────────► Checks constraint violations (allocations vs. net requirement, capacities)
      │
      ├────────────────────────────┐
      ▼ (if invalid & replans < 2)  ▼ (if valid or max replans reached)
   [replan]                    [explain] ──► [END]
(LLM reflects & relaxes)           ▲
      │                            │
      └────────────────────────────┘ (loops back to specialists)
```

1. **`parse_node`**: Invokes `parse_intent()` to extract structured intent (`product_query`, `quantity`, `horizon`, `objective`, `low_risk`).
2. **`supervisor_node`**: Dynamic supervisor that asks the LLM which specialist agents are needed (e.g., skips route optimization if the query only concerns warehouse inventory). Falls back deterministically if offline.
3. **`rag_node`**: Performs Agentic RAG. Uses the LLM to expand user queries into corporate domain terminology, queries `document_chunks` using hybrid dense (cosine distance) + sparse (`plainto_tsquery`) retrieval fused by Reciprocal Rank Fusion (RRF), and retrieves the top 6 evidence chunks.
4. **`specialists_node`**: Executes the selected domain agents with applied scenario patches (e.g. demand multipliers or disabled suppliers).
5. **`solve_node`**: Bundles agent findings into an `AgentBundle` and solves the Mixed-Integer Linear Program.
6. **`validate_node`**: Runs programmatic integrity checks: verifies that allocated units fulfill net requirements and do not exceed monthly supplier capacities.
7. **`should_replan`** (Conditional Edge): If validation fails and `replan_count < MAX_REPLAN` (default: 2), routes to `replan`; otherwise routes to `explain`.
8. **`replan_node`**: Analyzes the specific failure issues using LLM reflection to make targeted relaxations (e.g., relaxing max lead time or toggling low-risk constraints), incrementing the replan counter.
9. **`explain_node`**: Composes an explainable executive briefing citing solver status, per-supplier units, freight routes, composite risk, and retrieved RAG policies, stamped with synthetic data disclaimers.

---

## 5. Mathematical Optimization Model (`backend/app/optimization/solver.py`)

The solver uses Google OR-Tools with CBC/SCIP mixed-integer programming backends:

### Decision Variables
- $x_{s,r} \in \mathbb{Z}_{\ge 0}$: Integer quantity of units sourced from supplier $s$ along transportation route $r$.

### Objective Function
$$\min \sum_{(s,r) \in \text{Lanes}} \Big( P_s + C_r \cdot F_r + H_w + \text{RiskPenalty}(s) \Big) \cdot x_{s,r}$$

Where:
- $P_s$: Contractual supplier unit price.
- $C_r$: Base transport cost per unit on route $r$.
- $F_r$: Dynamic route fuel multiplier.
- $H_w$: Warehouse holding cost per unit.
- $\text{RiskPenalty}(s)$: Weighted penalty based on supplier reliability and risk tier:
  $$\text{RiskPenalty} = \text{weight} \cdot (1 - \text{reliability}_s) \cdot 100 + (15.0 \text{ if high risk tier else } 0)$$

### Constraints
1. **Demand Satisfaction**:
   $$\sum_{(s,r) \in \text{Lanes}} x_{s,r} \ge \text{NetRequirement}$$
2. **Supplier Monthly Capacity**:
   $$\forall s: \sum_{r} x_{s,r} \le \text{Capacity}_s$$
3. **Minimum Order Quantity (MOQ)**:
   $$x_{s,r} > 0 \implies \sum_r x_{s,r} \ge \text{MOQ}_s$$
4. **Route Capacity**:
   $$\forall r: \sum_{s} x_{s,r} \le \text{Capacity}_r$$
5. **Low-Risk Sourcing Restrictions** (when `low_risk=True`):
   - Excludes high-risk tier suppliers unless relaxed during replanning.
   - Enforces a minimum supplier reliability threshold ($\ge 0.70$).
   - Limits single-supplier concentration to $\le 60\%$ of total procurement.

---

## 6. Hybrid RAG Architecture (`backend/app/rag/`)

To ground supply chain recommendations in official corporate playbooks and policies, SupplyChainAI implements a two-stage hybrid retrieval mechanism:

1. **Document Ingestion (`ingest.py`)**:
   - Parses Markdown files in `data/knowledge/`.
   - Chunks text into semantic sections.
   - Generates 768-dimensional embeddings using Gemini `text-embedding-004` (or deterministic L2-normalized pseudo-random mock vectors when offline).
   - Generates English full-text search tsvectors (`to_tsvector('english', content)`).
2. **Hybrid Retrieval & Reciprocal Rank Fusion (`search.py`)**:
   - **Dense Search**: Queries pgvector using cosine distance (`<=>` operator):
     $$\text{score}_{\text{dense}} = 1 - (\text{embedding} \Leftrightarrow \vec{q})$$
   - **Sparse Search**: Queries PostgreSQL full-text search with ranking:
     $$\text{score}_{\text{sparse}} = \text{ts\_rank}(\text{tsv}, \text{plainto\_tsquery}('english', q))$$
   - **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse ranks with $k=60$:
     $$\text{RRF}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + \text{rank}_m(d)}$$
   - **Lexical Overlap Re-ranking**: Light lexical re-ranker boosts chunks sharing domain keywords with the expanded query.

---

## 7. What-If Stress-Testing Engine (`backend/app/whatif/engine.py`)

The platform supports rapid counterfactual simulations without altering baseline master data:

- **Supported Scenarios**:
  - `demand_increase`: Scales demand by $+X\%$.
  - `supplier_failure`: Completely disqualifies a designated supplier (`SUP-C`).
  - `price_increase`: Inflates raw material prices across vendors.
  - `fuel_increase`: Applies a fuel surcharge multiplier to all transport lanes.
  - `route_disruption`: Simulates port closure or freight lane blockage.
  - `inventory_shortage`: Reduces available stock across distribution centers.
- **Differential Analysis (`diff_results`)**:
  Computes precise baseline vs. scenario deltas for:
  - Total landed cost
  - Longest fulfillment lead time (hours)
  - Composite risk score
  - Unmet demand units

---

## 8. Human-in-the-Loop (HITL) Governance Gate (`backend/app/api/decisions.py`)

To prevent unauthorized or autonomous deployment of supply chain plans, SupplyChainAI features an enterprise-grade HITL decision gate:

```
                      ┌───────────────────────────┐
                      │ Optimized Plan Generated  │
                      │ (Status: PENDING_REVIEW)  │
                      └─────────────┬─────────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                    ▼
        ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
        │   APPROVE   │      │   REJECT    │      │  OVERRIDE   │
        └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
               │                    │                    │
               ▼                    ▼                    ▼
     Planner ID & time     Lineage-tracked re-   Validates override
     recorded. Plan unlocked  optimization run    against capacities.
     as final recommendation. triggered.         Approved with override.
```

1. **`approve`**: Signs off on the plan. Records `hitl_reviewed_by`, timestamp, and planner comments. Unlocks the final executive recommendation in the UI.
2. **`reject`**: Flags the plan as unviable. Persists rejection feedback and automatically triggers a new optimization run linked via `parent_run_id` for lineage auditing.
3. **`override`**: Allows human planners to manually input custom supplier allocation volumes. The system validates overrides via `validate_override_allocations()` ensuring manual volumes do not exceed supplier monthly capacities or fall below net requirements.

---

## 9. Frontend Architecture (`frontend/src/App.tsx`)

The frontend is a reactive single-page dashboard built with React 18, TypeScript, and Vite:

- **Natural Language Problem Input**: Multi-line query prompt pre-loaded with typical supply chain scenarios.
- **KPI Metrics Bar**: Real-time display of Forecasted Units, Total Cost, Delivery Hours, Composite Risk Score, and Optimization Status.
- **Supplier Allocation & Route Matrices**: Interactive tables detailing unit quantities, supplier names, route lanes, transport modes, and line costs.
- **Inventory Distribution Center Grid**: On-hand, reserved, available, and safety stock levels per DC.
- **What-If Scenario Simulator**: Dropdowns and inputs to stress-test supplier failures, demand spikes, or fuel price shocks with delta comparison tables.
- **Mandatory HITL Governance Gate**:
  - Color-coded status badge (`PENDING_REVIEW` [Yellow], `APPROVED` [Green], `REJECTED` [Red], `APPROVED_WITH_OVERRIDE` [Blue]).
  - Planner credential and review comment inputs.
  - Approve, Reject, and Override triggers.
  - **Locked Recommendation Panel**: Prevents viewing or acting on detailed execution steps until explicit human approval is logged.
- **Retrieved Evidence Viewer**: Displays pgvector-retrieved policy snippets, relevance scores, and document titles.
- **Agent Trace & Audit Log**: Step-by-step chronological audit log of internal agent transitions and human approval events.

---

## 10. Verification & Quality Assurance

The system is tested across multiple layers:

1. **Unit & Pipeline Tests (`backend/tests/`)**:
   - `test_pipeline.py`: Tests the full LangGraph pipeline from intent parsing to OR-Tools solve.
   - `test_api.py`: Tests REST endpoints (`/health`, `/catalog`, `/decisions`, `/what-if`).
   - `test_extended_verification.py`: 23 extensive regression tests covering RAG RRF fusion, constraint validation, supervisor routing, replan relaxation, and HITL gate states.
2. **System Verification Suite (`verify_system.py`)**:
   - Automated 5-stage health check, catalog verification, baseline decision run, what-if stress test, and frontend reachability validation.
3. **Research & Benchmarking Scripts (`scripts/`)**:
   - `benchmark_rag_ablation.py`: Validates performance gain of hybrid search over dense-only and sparse-only baselines.
   - `evaluate_llms.py`: Tests intent parsing accuracy across different prompt strategies and models.

---

## 11. How to Run the Platform

### Option A: Local Development
```powershell
# 1. Start PostgreSQL with pgvector
docker run -d --name sc-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16

# 2. Run backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Run frontend
cd ..\frontend
npm install
npm run dev
```

### Option B: Docker Compose
```powershell
docker compose up --build
```
- Frontend UI: `http://localhost:5173`
- Backend Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`
