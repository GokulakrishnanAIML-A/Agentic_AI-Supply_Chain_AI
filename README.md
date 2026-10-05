# SupplyChainAI — Autonomous Supply Chain Decision Intelligence Platform

[![CI Pipeline](https://github.com/your-org/SupplyChainAI/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/SupplyChainAI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-MILP%20Solver-orange.svg)](https://developers.google.com/optimization)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL%2016-pgvector-336791.svg)](https://github.com/pgvector/pgvector)

**SupplyChainAI** is a multi-agent decision intelligence platform that combines natural language understanding, hybrid retrieval-augmented generation (RAG), and rigorous Mixed-Integer Linear Programming (Google OR-Tools) with human-in-the-loop (HITL) governance for enterprise supply-chain procurement and rebalancing.

> **Core Architectural Principle (Rule R5):**
> Large Language Models (LLMs) **never** calculate order quantities, financial costs, unit allocations, or safety stocks. All operational numbers and allocations are determined strictly by deterministic domain logic and mathematical MILP optimization.

---

## 1. System Architecture

```
                                  USER QUERY (Plain English)
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │    Intent Parser (Regex / LLM)   │
                             │  Extracts SKU, Qty, Target Date  │
                             └──────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR / LANGGRAPH SUPERVISOR                                    │
│                                                                                                 │
│  ┌─────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────────┐  │
│  │    Hybrid RAG Engine    │   │      Demand Agent        │   │       Supplier Agent         │  │
│  │ Dense (768d) + Sparse   │   │  Rolling-Origin Forecast │   │  Capacity, MOQs, Reliability │  │
│  │ Corporate Policy Docs   │   │  (Naive + 3MA + Seasonal)│   │  Risk Tiering & Penalties    │  │
│  └─────────────────────────┘   └──────────────────────────┘   └──────────────────────────────┘  │
│                                                                                                 │
│  ┌─────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────────┐  │
│  │       Route Agent       │   │      Inventory Agent     │   │         Risk Agent           │  │
│  │ Shipping Lanes, Modes,  │   │  Net Req = max(0, D+SS-A)│   │  Plan Risk (0-100) vs        │  │
│  │ Port Strikes, Fuel Mult │   │  Warehouse Space Limits  │   │  Disruption Exposure         │  │
│  └─────────────────────────┘   └──────────────────────────┘   └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │     OR-Tools MILP Solver         │
                             │  Minimizes Landed Cost + Risk    │
                             │  Subject to Cap, MOQ, Space, Lane│
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │     Hard Invariant Validator     │
                             │  Verified against all predicates │
                             └──────────────────────────────────┘
                                      │                │
                        (Violations) │                │ (Feasible / Optimal)
                                      ▼                │
                       ┌────────────────────────────┐  │
                       │   Bounded Replan Node      │  │
                       │   Whitelisted Relaxations  │  │
                       │   Emits `degraded: true`   │  │
                       └────────────────────────────┘  │
                                      │                │
                                      └───────┬────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │  Explanation & Faithfulness Node │
                             │  Rejects hallucinated numbers;   │
                             │  Falls back to verified template │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │   HITL Governance & Audit Log    │
                             │  Append-only `decision_events`   │
                             │  Server-side Execution Lock      │
                             │  Approve / Reject / Override     │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │     React + Vite Planner UI      │
                             └──────────────────────────────────┘
```

---

## 2. 5-Minute Quickstart

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Recommended)
- **OR** Python 3.11+ and Node.js 20+ for local native execution.

### Option A: Docker Compose (Fastest)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/SupplyChainAI.git
   cd SupplyChainAI
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   ```

3. **Build and launch containers:**
   ```bash
   docker compose up --build
   ```

4. **Access the application:**
   - **Planner Web Dashboard:** [http://localhost:5173](http://localhost:5173)
   - **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Healthcheck:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Local Native Setup (Developer Mode)

1. **Set up Python backend virtual environment:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate    # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

2. **Start PostgreSQL with pgvector:**
   ```bash
   docker compose up -d db
   ```

3. **Start the FastAPI backend server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Start the React frontend:**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

---

## 3. Operational Modes

SupplyChainAI is designed to run in multiple environments without mandatory third-party API dependencies:

| Component | `mock` (Default) | `local` | `gemini` / `openai` |
|---|---|---|---|
| **LLM Provider** | Deterministic rule-based fallbacks (0 API calls, $0 cost) | Local Ollama (`llama3.1`) | Google Gemini (`gemini-2.0-flash`) or OpenAI (`gpt-4o-mini`) |
| **Embeddings** | Deterministic pseudo-embeddings (test fixture only) | `sentence-transformers/all-mpnet-base-v2` (768d, offline) | Google `text-embedding-004` (768d) |
| **Solver** | Google OR-Tools MILP (deterministic) | Google OR-Tools MILP | Google OR-Tools MILP |
| **Database** | PostgreSQL 16 + pgvector | PostgreSQL 16 + pgvector | PostgreSQL 16 + pgvector |

---

## 4. Testing, Benchmarks & Evaluation

### Run Unit and Integration Tests
```bash
# Run test suite with invariant checks
pytest backend/tests/ -v

# Run with statement coverage
pytest backend/tests/ --cov=backend/app --cov-report=term-missing
```

### Run Evaluation Benchmarks
SupplyChainAI includes reproducible benchmark harnesses with empirical results stored in `results/*.json`:

```bash
# Run all benchmark harnesses and compile evaluation report
make eval

# Individual benchmarks:
make eval-rag        # Evaluates dense vs sparse vs RRF retrieval (45 queries, 95% bootstrap CI)
make eval-solver     # Evaluates OR-Tools MILP across 50 seeded stress scenarios (violations, cost gap)
make eval-intent     # Intent parsing exact-match and field-level F1 across 100 labeled queries
make eval-forecast   # Rolling-origin CV (h=1) across naive, seasonal, and blended estimators
make eval-ablation   # Measures real effect of LLM supervisor, query expansion, replanner, & faithfulness
```

### Claims Register Verification
Every metric reported in the documentation is verified against active benchmark artifacts:
```bash
python scripts/build_report.py
```

---

## 5. Human-in-the-Loop (HITL) & Governance

1. **Append-Only Audit Log:** All decisions and modifications are recorded in `decision_events` with immutable timestamps and user identities.
2. **Reviewer Authentication:** Planners authenticate using secure `X-API-Key` headers tied to recognized accounts (e.g., `alice`, `bob`, `lead_planner`).
3. **Server-Side Recommendation Lock:** Recommendations remain masked (`"recommendation": null`) until explicitly approved by an authorized reviewer.
4. **Structured Rejection:** Rejections specify concrete operational reasons (e.g., supplier exclusion, maximum supplier share), which automatically instantiate a modified child simulation.
5. **Full-Fidelity Overrides:** Manual planner overrides are evaluated against all mathematical constraints (MOQs, capacities, route closures, warehouse space). Any policy violations require explicit acknowledgment and are logged with cost delta against optimal (`cost_delta_vs_optimal`).

---

## 6. Known Scope & Limitations

- **Synthetic Dataset:** Historical demand, supplier profiles, and weather anomalies are synthetically generated for benchmark stability.
- **Single-Period Optimization:** The MILP solver optimizes a single procurement cycle rather than multi-period model predictive control (MPC).
- **Authentication:** Reviewer identity uses API key headers suitable for internal microservices; OAuth2/OIDC integration is recommended for multi-tenant production.

---

## 7. Project Structure

```
SupplyChainAI/
├── backend/
│   ├── app/
│   │   ├── agents/          # Domain agents (demand, inventory, supplier, route, risk)
│   │   ├── api/             # FastAPI routers, endpoints, auth dependencies, schemas
│   │   ├── core/            # Configuration and settings
│   │   ├── db/              # SQLAlchemy models, sessions, and repositories
│   │   ├── graph/           # LangGraph supervisor, nodes, faithfulness guards
│   │   ├── llm/             # Structured LLM contract, factory, and fallbacks
│   │   ├── optimization/    # Google OR-Tools MILP solver and plan evaluator
│   │   ├── rag/             # 768d hybrid vector search and document ingestion
│   │   └── validation/      # Invariant validator (shared predicates)
│   └── tests/               # Pytest suite (invariants, invariance, HITL, RAG, nodes)
├── frontend/                # React + Vite + TypeScript planner dashboard
├── data/                    # Seed datasets and evaluation query benchmarks
├── docs/                    # Architecture, claims register, and evaluation reports
├── results/                 # Ground-truth JSON benchmark results
├── scripts/                 # Benchmark harnesses (RAG, solver, intent, forecast, ablations)
├── docker-compose.yml       # Containerized environment
├── Makefile                 # Unified execution commands
└── README.md
```
