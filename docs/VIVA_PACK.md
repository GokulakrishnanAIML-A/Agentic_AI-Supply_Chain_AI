# SupplyChainAI — Comprehensive Viva Voce & Technical Defense Pack

This guide provides technical answers to 20 potential examination and architecture defense questions regarding SupplyChainAI.

---

### Q1: Why use Mixed-Integer Linear Programming (MILP) instead of letting an LLM generate the allocation directly?
**Answer:**
LLMs are probabilistic autoregressive token generators with no formal guarantees regarding arithmetic accuracy, constraint satisfaction, or optimality. A complex supply chain allocation involves multi-dimensional constraints (vendor capacities, non-linear discrete MOQs, storage limits, route disruptions, and risk penalty trade-offs). An LLM attempting this problem frequently hallucinates quantities, breaches binary MOQ thresholds, and produces sub-optimal allocations. In contrast, Google OR-Tools MILP guarantees finding the mathematically proven global minimum cost in milliseconds while guaranteeing zero constraint violations.

---

### Q2: What is the exact mathematical formulation of the MOQ constraint?
**Answer:**
Minimum Order Quantity (MOQ) is a semi-continuous constraint. If supplier $s$ is chosen ($y_s = 1$), order quantity $x_s \ge \text{MOQ}_s$. If $y_s = 0$, $x_s = 0$. We formulate this using binary indicator variables $y_s \in \{0, 1\}$ and the Big-M relaxation:
$$\sum_r x_{s,r} \le \text{Cap}_s \cdot y_s$$
$$\sum_r x_{s,r} \ge \text{MOQ}_s \cdot y_s$$
This ensures the solver never outputs an infeasible allocation where $0 < x_s < \text{MOQ}_s$.

---

### Q3: How do you prevent LLM hallucinations from corrupting the final decision?
**Answer:**
Through a multi-layered defense-in-depth architecture:
1. **Rule R5 (Neurosymbolic Separation):** LLM outputs are never consumed as numbers by the solver.
2. **Pydantic Whitelist Validation:** All structured LLM responses (e.g., intent, supervisor routing, replan relaxations) are parsed into strict Pydantic schemas with closed enumerations.
3. **Supervisor Hard Guards:** For procurement intents, the supervisor graph unconditionally enforces the inclusion of the required agent set `{supplier, route, inventory}`, regardless of LLM choices.
4. **Explanation Faithfulness Guard (`unfaithful_numbers`):** Before presenting the natural-language explanation to the user, a regex extractor compares all numeric tokens against the ground-truth facts returned by OR-Tools. If any unrecognized number is detected, the text is discarded and replaced with a deterministic template.

---

### Q4: Why is LangGraph chosen for agent orchestration rather than AutoGen or standard LangChain chains?
**Answer:**
Supply chain decision pipelines require deterministic state transitions, cyclic error handling, and bounded re-planning. LangGraph models the workflow as a stateful Directed Acyclic Graph (DAG) with cyclic edges. It allows explicit state schemas (`SupplyChainState`), conditional branching (e.g., routing to `replan_node` if `validator` detects infeasibility), and strict step budgets (`max_replan=2`), ensuring execution never enters an infinite loop.

---

### Q5: How is the Inventory Net Requirement calculated, and why was the legacy formula flawed?
**Answer:**
The correct formula for net procurement requirement is:
$$\text{Net Requirement} = \max(0, \text{Demand} + \text{Safety Stock} - \text{Available Stock})$$
where $\text{Available Stock} = \sum \max(0, \text{On Hand} - \text{Reserved})$.
The legacy implementation computed $D - \text{Avail} + \max(0, \text{SS} - \text{Avail})$, which erroneously double-counted available stock whenever $\text{Avail} < \text{SS}$ (resulting in $D + \text{SS} - 2 \cdot \text{Avail}$). We fixed this with a pure, tested function that guarantees safety stock replenishment.

---

### Q6: What is Hybrid RAG and why is Reciprocal Rank Fusion (RRF) used?
**Answer:**
Hybrid RAG combines:
1. **Dense Retrieval (Semantic Search):** 768-dimensional embeddings (`sentence-transformers/all-mpnet-base-v2` or Gemini) via pgvector cosine distance to capture conceptual meaning (e.g., "supply bottleneck policy").
2. **Sparse Retrieval (Lexical Search):** PostgreSQL full-text search (`ts_rank_cd` on `tsvector`) to match specific product codes and acronyms (e.g., "PROD-A", "MOQ", "DC-02").
RRF merges the ranked lists without requiring score normalization:
$$\text{RRF Score}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + \text{rank}_m(d)}$$
with $k=60$, ensuring documents highly ranked across both retrieval methods surface at the top.

---

### Q7: How does your benchmark prove that Hybrid RAG is superior to pure dense retrieval?
**Answer:**
In our RAG benchmark across 45 queries with 95% bootstrap confidence intervals (`results/rag.json`), Hybrid RAG with Lexical Reranking achieved **95.0% Recall@3** (MRR: 0.933, nDCG@3: 0.941), significantly outperforming pure sparse search (Recall@3: 45.0%) and improving edge-case precision on SKU-specific queries.

---

### Q8: What happens when the user's demand is mathematically impossible to fulfill?
**Answer:**
1. The OR-Tools solver returns status `INFEASIBLE`.
2. The `validator` identifies the binding constraint (e.g., supplier capacity exhaustion or lead time horizon).
3. The workflow routes to `replan_node`, which evaluates bounded, whitelisted relaxations (e.g., expanding lead time window up to 30 days or relaxing single-supplier concentration limits).
4. If feasible under relaxation, the plan is marked `degraded: true` and the relaxations are documented.
5. If still impossible after 2 iterations, the system cleanly returns status `INFEASIBLE` with the binding constraint explicitly named, rather than returning a silent partial plan.

---

### Q9: Why decouple `plan_risk` and `disruption_exposure`?
**Answer:**
In earlier versions, simulating a supplier failure sometimes caused the overall risk score to drop because the solver shifted volume to a lower-risk supplier. This confused planners. We split the metrics into:
- **`plan_risk` (0–100):** The intrinsic weighted risk of the chosen vendors and lanes.
- **`disruption_exposure`:** The external environmental risk of active port strikes, weather anomalies, and geopolitical disruptions affecting the network.

---

### Q10: How does the Human-in-the-Loop (HITL) governance model ensure audit compliance?
**Answer:**
1. **Append-Only Event Ledger:** Table `decision_events` maintains an immutable audit log of every creation, approval, rejection, and override.
2. **Token-Derived Identity:** Reviewer usernames are extracted server-side from validated API keys (`X-API-Key`), preventing client-side identity spoofing.
3. **Server-Side Recommendation Lock:** The API redacts operational execution details (`"recommendation": null`) until an authorized reviewer approves the plan.
4. **Structured Rejections:** Rejecting a plan requires operational feedback (e.g., excluding a vendor), which spawns a linked child run for transparent lineage tracking.

---

### Q11: How do you validate manual planner overrides?
**Answer:**
Manual overrides are evaluated through `evaluate_plan()` in `backend/app/optimization/solver.py`, which runs the exact same mathematical predicates as the solver. If an override violates MOQ, exceeds supplier capacity, or overfills warehouse space, it is rejected. If an override violates a soft policy (e.g., supplier concentration), it requires explicit planner acknowledgement and records the `cost_delta_vs_optimal`.

---

### Q12: How is the demand forecast calculated and validated?
**Answer:**
The demand agent computes a statistical blend of:
1. Seasonal Naive ($t-12$ value)
2. 3-Month Trailing Moving Average (3MA)
We evaluated this using a rolling-origin cross-validation harness ($h=1$, $\text{min\_train}=12$) across all SKU-warehouse pairs (`results/forecast.json`), achieving a baseline **MAPE of 6.49%** on synthetic seasonal data. If a user explicitly specifies a quantity, the user quantity takes precedence, and any significant deviation ($>25\%$) from forecast emits a planning warning.

---

### Q13: What did the agentic ablation study reveal?
**Answer:**
Our ablation experiments (`results/ablation.json`) showed:
- **Rule-based Supervisor vs LLM Supervisor:** Rule-based routing achieved 100% precision on required agent execution with 0.0ms latency overhead, whereas unconstrained LLM routing occasionally dropped critical nodes.
- **Replan Mechanism:** Achieved a **50.0% recovery rate** on initially infeasible high-demand stress scenarios.
- **Faithfulness Guard:** Achieved **100% faithfulness** across generated explanations by dropping hallucinated numbers.

---

### Q14: How is determinism guaranteed across the platform?
**Answer:**
1. All random number generators and bootstrap evaluators use fixed `seed=42`.
2. All LLM calls enforce `temperature=0`.
3. OR-Tools MILP solver utilizes deterministic branch-and-bound algorithms.
4. Test suite includes an invariance test (`test_llm_invariance.py`) proving that identical supply-chain intents always yield identical numerical allocations regardless of LLM provider.

---

### Q15: What is the latency profile of the decision pipeline?
**Answer:**
In mock/local mode, the entire pipeline executes in **under 25 milliseconds** (OR-Tools solve time p50: 7.02ms, p95: 12.18ms). When integrated with remote LLM APIs (e.g., Gemini 2.0 Flash), end-to-end latency is approximately 800ms–1.5s, dominated by network I/O.

---

### Q16: What database schema is used for vector similarity search?
**Answer:**
PostgreSQL 16 with the `pgvector` extension. Chunks are stored in `document_chunks` with an `embedding vector(768)` column indexed by an HNSW or IVFFlat index, alongside a `tsv tsvector` column indexed with GIN for full-text search.

---

### Q17: What are the primary known limitations of the current implementation?
**Answer:**
1. **Synthetic Data:** Order histories, supplier catalogs, and weather events are synthetically modeled.
2. **Single-Period Optimization:** Solves a single procurement cycle rather than dynamic multi-period inventory control (MPC).
3. **Demo Authentication:** API-key mapping in headers is designed for single-organization internal microservices rather than multi-tenant OAuth2/OIDC.

---

### Q18: What is the difference between production deployment and development mode?
**Answer:**
- **Development (`docker-compose.yml`):** Uses hot-reloading (`uvicorn --reload`), Vite dev server on port 5173, mounted local source directories.
- **Production (`docker-compose.prod.yml`):** Multi-stage built React static assets served via high-performance Nginx on port 80, backend executed with multi-worker Uvicorn without file watchers, and read-only data mounts.

---

### Q19: What role does Google OR-Tools play in the architecture?
**Answer:**
OR-Tools provides the underlying Mixed-Integer Linear Programming engine (using the CBC or SCIP solver backend). It transforms our mathematical objective and constraint matrices into optimal decision variable vectors ($x_{s,r}$) representing exact unit orders per supplier and shipping lane.

---

### Q20: What was the division of work between inherited boilerplate and your custom hardening?
**Answer:**
- **Inherited Boilerplate:** Initial project directory structure, basic FastAPI skeletons, and synthetic CSV datasets.
- **My Hardening & Engineering:**
  1. Complete fix of B-01 net requirement calculation and safety stock logic.
  2. B-02 OR-Tools MILP solver reformulation with binary MOQ indicator variables and warehouse space constraints.
  3. B-03 Bounded replanning with closed whitelist schemas and `degraded: true` transparency.
  4. B-07 Invariant validator and shared constraint predicate alignment.
  5. B-10 Numeric faithfulness guard and hallucination drop mechanism.
  6. B-11 Decoupled risk metric architecture (`plan_risk` vs `disruption_exposure`).
  7. B-09 Complete Human-in-the-Loop governance: append-only `decision_events`, reviewer API key auth, structured rejection re-run, full-fidelity override engine, and server-side recommendation lock.
  8. T4.* 5 reproducible evaluation benchmark harnesses with empirical results stored in `results/*.json` and verifiable `docs/CLAIMS.md`.
