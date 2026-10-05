# SupplyChainAI — Fix, Hardening & Agent Execution Plan

**Prepared:** 2026-10-05 · **Scope:** mini project hardening (correctness → agentic integrity → HITL → real evaluation → docs → release)
**Basis:** audit of `IMPLEMENTATION_AND_VERIFICATION_REPORT.md`, `GUIDELINES_EVALUATION_REPORT.md`, `PROJECT_ARCHITECTURE_AND_MODULE_WORKINGS.md`.
**Important:** the *code was not inspected*. Every task begins with a **VERIFY** step against the real repo. Where docs and code disagree, code wins and the docs get fixed.

---

## 0. How to use this document

| Reader | Use |
|---|---|
| **Executor agent (Claude Code / similar)** | Follow §2 rules, then run task cards in §4–§10 in dependency order (§3). Log every task in `docs/EXECUTION_LOG.md` (template §13). |
| **You (student)** | Review each phase gate (§11), approve `DECISION NEEDED` items, own the final audit (§13.3). |
| **Reviewer / examiner** | Read `docs/CLAIMS.md` + `results/*.json` — every number must trace there. |

Legend: `[ ]` open · `[x]` done · **VERIFY** = confirm in code before editing · **DECISION NEEDED** = human choice required, agent must stop that task.

---

## 1. Ground truth: issue register

| ID | Sev | Module | Issue | Evidence | Fix task |
|---|---|---|---|---|---|
| B-01 | **Critical** | `agents/inventory.py` | Net requirement double-counts available stock: `D − avail + max(0, SS − avail)` = `D + SS − 2·avail` when `avail < SS`. Run #52: 10,000 − 1,140 + 610 = 9,470; correct (SS replenished) = 10,610. | Docs formula + numbers | T1.1 |
| B-02 | High | `optimization/solver.py` | MOQ written as implication (non-linear) with no binary `y_s` listed; warehouse inbound-capacity constraint present in one doc, absent in another. | Doc §5 vs earlier §6 | T1.2 |
| B-03 | High | `graph/nodes.py` (`replan_node`) | Replan silently relaxes policy constraints; "guaranteed feasible fallback" claim contradicted by `test_extreme_demand_infeasible`. | Docs | T2.3 |
| B-04 | High | `scripts/*`, docs | Evaluation numbers unsupported: LLM baseline (32%, $15–45/1k, 1.8–3.5 s) cannot come from a mock provider; RAG ablation on ~8 queries / 7 docs with pseudo-random mock embeddings; "100% coverage" unmeasured. | `llm_provider: mock` | T4.* |
| B-05 | High | docs | Cross-doc contradictions (table below). | 3 docs | T0.3, T5.4 |
| B-06 | Med | `agents/demand.py`, `graph/nodes.py` | Forecast (10,392) ignored — `demand_to_meet`=10,000. No holdout MAPE; 55/45 vs 60/40 weights arbitrary. | Run #52 | T1.3 |
| B-07 | Med | `validation/validator.py` | Validator `|Σx−D|≤1` vs solver `Σx ≥ D` → MOQ overshoot can trigger spurious replan. | Docs | T1.4 |
| B-08 | Med | `graph/nodes.py` (`supervisor_node`) | LLM may skip agents the solver requires. | Docs | T2.2 |
| B-09 | Med | `api/decisions.py`, `db/models.py`, frontend | HITL: `reject` reruns identical inputs (deterministic → same plan); `override` validation may miss MOQ/route/warehouse/concentration; "immutable audit" is mutated in place; `reviewed_by` free text; lock panel may be UI-only. | Docs | T3.* |
| B-10 | Med | `graph/nodes.py` (`explain_node`) | Explanation text not checked against solver output. | Docs | T2.4 |
| B-11 | Low | `agents/risk.py`, `whatif/engine.py` | `supplier_failure` lowers risk score (49.7→44.4) — needs split metric/explanation. | Run output | T1.5 |
| B-12 | Low | repo | No README/.env.example/CI; dev server shown as "production"; absolute `e:/` paths; self-assigned "A+". | Docs | T5.* |
| B-13 | Med | tests | LLM code paths never exercised (mock only). | `verify_system.py` | T2.1, T2.5, T4.* |
| B-14 | Low | tests | Coverage claimed ("100%") but never measured. | Guidelines report | T0.4, T3.6 |

**Cross-doc contradictions to resolve (T0.3):**

| Item | Earlier reports | Architecture doc |
|---|---|---|
| Embedding dim | 384 | `Vector(768)` |
| RRF | weights 0.6 / 0.4 | equal weights + lexical rerank |
| Sparse query | `websearch_to_tsquery`, `ts_rank_cd` | `plainto_tsquery`, `ts_rank` |
| Forecast blend | 60 / 40 | 55 / 45 |
| Low-risk rules | reliability ≥ 0.90; high-risk ≤ 15% | reliability ≥ 0.70; high-risk excluded |
| MILP vars | `x` + binary `y_s` | `x` only; MOQ as implication |
| Warehouse inbound cap | present | absent (route cap present) |
| Test count | 19 / 20 | 23 |
| Validate ↔ solve order | validate before solve (one diagram) | solve → validate |

---

## 2. Executor operating rules (non-negotiable)

1. **R1 Read before write.** `view` the target file, its tests, and callers before editing.
2. **R2 One task = one commit** on branch `fix/<phase>`; message `T1.1: <summary>`.
3. **R3 Never weaken tests.** No `skip`/`xfail`/deleted asserts to get green. A test may change only if it encoded a bug (e.g., B-01 expected value); log the justification.
4. **R4 Red → green.** For bug tasks: write failing test first, commit nothing until it fails for the right reason, then fix.
5. **R5 LLM never touches numbers.** Any LLM output reaching solver inputs passes a Pydantic whitelist schema with bounds; deterministic fallback always exists.
6. **R6 Evidence or it didn't happen.** Each gate saves artifacts to `docs/evidence/<task-id>/` (command output, diff stat, JSON).
7. **R7 Scope lock.** After each task run `git diff --stat`; files outside the task's **Files** list → stop, log, revert or justify.
8. **R8 No fabricated metrics.** Numbers in docs come only from `results/*.json`. Unrunnable eval → `status: "NOT_RUN"` and the claim is removed or labelled *estimate*.
9. **R9 Determinism.** `seed=42` for generators, scenario sampling, bootstrap; LLM `temperature=0`.
10. **R10 Smoke always green.** `python verify_system.py` must pass after every task (expected value changes allowed only via T1.6 golden update).
11. **R11 No secrets in git.** `.env` ignored; `.env.example` only.
12. **R12 Update the module audit matrix (§12) at the end of each task.**

**Stop conditions (agent must halt the task and log):**
- Same test fails after 2 fix attempts without a new hypothesis.
- A gate check fails.
- Scope lock (R7) violated.
- A policy choice is ambiguous → write `DECISION NEEDED: <question + options + recommendation>`, skip to independent tasks.
- Any change would alter solver numbers outside tasks T1.1/T1.2/T1.3.

**Standard task gate (G0) — run after every task:**
```bash
docker compose exec backend pytest -q -x
python verify_system.py
git diff --stat            # R7 scope check
```
Pass = 0 failures, `verify_system.py` prints 5/5, diff touches only listed files.

---

## 3. Task dependency graph

```
T0.1 → T0.2 → T0.3 → T0.4
                 │
                 ▼
        T1.1 → T1.2 → T1.4 → T1.6
          │      │
          ▼      ▼
        T1.3    T1.5
                 │
   ┌─────────────┴──────────────┐
   ▼                            ▼
T2.1 → T2.2 → T2.3 → T2.4 → T2.5      T4.1 → T4.2
                 │                          │
                 ▼                          ▼
T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T3.6   T4.3 → T4.4 → T4.5 → T4.6 → T4.7
                                                           │
                                         T5.1 → T5.2 → T5.3 → T5.4 → T5.5
                                                           │
                                                T6.1 → T6.2 → T6.3
```
Parallelizable: Phase 4 (T4.1–T4.2) can run alongside Phase 2/3 after T1.6. T4.3+ needs T2.* and T3.* done.

---

## 4. PHASE 0 — Baseline freeze & discrepancy audit

### T0.1 Environment & branch
- **Files:** none (repo setup)
- **Steps:** `git checkout -b fix/p0-baseline`; `docker compose up -d --build`; record versions (`python --version`, `pip freeze > docs/evidence/T0.1/pip_freeze.txt`, node, postgres, pgvector).
- **Commands:** `docker compose exec backend pytest -q | tee docs/evidence/T0.1/pytest_baseline.txt`
- **STOP-GATE:** containers healthy (`/api/v1/health` ok), baseline pytest result recorded **as-is** (record the real count — 19, 20, or 23).
- **Rollback:** none.

### T0.2 Golden baseline capture
- **Files:** `tests/golden/*.json` (new), `scripts/capture_golden.py` (new)
- **Steps:** run 3 canned queries (Product A 10k low-risk; Product A with `SUP-C` failure; a zero-requirement case) + all 6 what-if scenarios; dump `result_json` with seed fixed. Save as golden files.
- **STOP-GATE:** golden files exist; re-running `capture_golden.py` twice yields byte-identical output (determinism proof). If not → find nondeterminism (dict ordering, timestamps, run ids) and strip from comparison.
- **Evidence:** `docs/evidence/T0.2/determinism_diff.txt` (empty diff).

### T0.3 Discrepancy audit against code
- **Files:** `docs/AUDIT_DISCREPANCIES.md` (new)
- **VERIFY list (grep the code, don't trust docs):**
  ```bash
  grep -rn "Vector(" backend/app/db/models.py
  grep -rn "tsquery\|ts_rank" backend/app/rag/search.py
  grep -rn "0\.55\|0\.6\|0\.45\|0\.4" backend/app/agents/demand.py
  grep -rn "reliab\|0\.70\|0\.90\|0\.15\|0\.60" backend/app/optimization/solver.py
  grep -rn "BoolVar\|IntVar\|NumVar" backend/app/optimization/solver.py
  grep -rn "capacity_units" backend/app/optimization/solver.py
  grep -rn "def test_" backend/tests | wc -l
  sed -n '1,80p' backend/app/graph/graph.py   # edge order
  ```
- **Output:** one row per row of the §1 contradiction table: `code says X → docs to be changed to X` or `DECISION NEEDED`.
- **STOP-GATE:** every row has a resolution; no row left "unknown".

### T0.4 Coverage baseline
- **Files:** `backend/requirements-dev.txt` (pytest-cov), `docs/evidence/T0.4/coverage.txt`
- **Command:** `docker compose exec backend pytest --cov=app --cov-report=term-missing -q`
- **STOP-GATE:** real coverage % recorded. This replaces the "100% coverage" claim permanently.

**PHASE 0 GATE (§11-P0).**

---

## 5. PHASE 1 — Correctness fixes

### T1.1 Fix net requirement (B-01)
- **Files:** `backend/app/agents/inventory.py`, `backend/tests/test_inventory.py` (new)
- **VERIFY:** locate where `net` is computed and where `safety_gap` is consumed elsewhere (validator, explain, UI).
- **DECISION NEEDED (record in log):** policy = safety stock is rebuilt after demand is served (recommended). Alternative = safety stock may be consumed. Default to recommended unless the human decides otherwise.
- **Red tests first:**
  ```python
  from app.agents.inventory import net_requirement

  def test_no_double_count():   assert net_requirement(10000, 1140, 1750) == 10610
  def test_surplus_is_zero():   assert net_requirement(1000, 5000, 500) == 0
  def test_ss_topup():          assert net_requirement(1000, 1200, 500) == 300
  def test_zero_everything():   assert net_requirement(0, 0, 0) == 0
  ```
- **Fix:**
  ```python
  def net_requirement(demand: int, available: int, safety_total: int) -> int:
      """Units to procure so that, after serving `demand`, stock == safety_total."""
      return max(0, demand + safety_total - available)
  ```
  Replace inline computation with this pure function; keep per-warehouse `available = Σ max(0, on_hand − reserved)`.
- **Expected side effects:** Product A net req moves from 9,470 → ~10,610 (**VERIFY** SS total = 1,750). Cost rises; solver may need more suppliers or become infeasible → record in T1.6, do not "fix" by touching capacities.
- **STOP-GATE:** 4 new tests pass; old tests asserting 9,470 are the *only* tests allowed to change (R3) and each change is logged.
- **Rollback:** `git revert` the single commit.

### T1.2 Solver formulation audit & fix (B-02)
- **Files:** `backend/app/optimization/solver.py`, `backend/tests/test_solver_invariants.py` (new)
- **VERIFY:** which variables/constraints exist today. Compare with target model below; fix only gaps.
- **Target model:**
  - `x[s,r] ∈ ℤ≥0` per feasible (supplier, route) lane; `y[s] ∈ {0,1}`.
  - `Σ_r x[s,r] ≤ cap[s]·y[s]` · `Σ_r x[s,r] ≥ moq[s]·y[s]`
  - `Σ_s x[s,r] ≤ route_cap[r]` (disrupted route → cap 0)
  - `Σ_{(s,r)→w} x ≤ wh_capacity[w] − on_hand[w]`
  - `Σ x ≥ net_req`
  - low-risk (when active & not relaxed): weighted reliability ≥ θ_rel, high-risk share ≤ α (or excluded — **DECISION NEEDED**, pick one and make code, docs, tests agree), per-supplier share ≤ 0.60.
  ```python
  y = {s: solver.BoolVar(f"y_{s}") for s in suppliers}
  solver.Add(sum(x[s, r] for r in lanes[s]) <= cap[s] * y[s])
  solver.Add(sum(x[s, r] for r in lanes[s]) >= moq[s] * y[s])
  solver.Add(sum(x[l] for l in into_wh[w]) <= wh_cap[w] - on_hand[w])
  ```
- **Invariant tests (seeded random scenarios, ≥ 200 cases, no new deps):** for every returned plan:
  1. `Σx ≥ net_req` (status OPTIMAL/FEASIBLE)
  2. each supplier `≤ cap`; `0 < Σ < moq` never occurs
  3. each warehouse inbound `≤ space`
  4. each route `≤ route_cap`; closed routes get 0
  5. if low-risk active & not relaxed → concentration/reliability constraints hold
  6. infeasible input → status `INFEASIBLE`, **not** a silent partial plan
- **STOP-GATE:** 200/200 invariant cases pass; solve time p95 within 2× baseline (record).
- **Rollback:** revert commit.

### T1.3 Forecast: validate it, then give it a job (B-06)
- **Files:** `backend/app/agents/demand.py`, `backend/app/graph/nodes.py` (demand selection only), `scripts/eval_forecast.py` (new), `backend/tests/test_forecast.py` (new)
- **Policy (implement):**
  ```python
  if intent.quantity:                       # explicit user quantity wins
      demand = intent.quantity
      deviation = abs(demand - fc) / max(fc, 1)
      trace.warn("qty_vs_forecast", deviation) if deviation > 0.25 else None
  else:
      demand = fc                           # no quantity → use forecast
  ```
- **Forecast evaluation (rolling origin, h=1, min_train=12) per SKU×warehouse:**
  ```python
  def rolling_origin(series, fn, min_train=12):
      errs = []
      for t in range(min_train, len(series)):
          pred = fn(series[:t]); errs.append(abs(series[t]-pred)/max(series[t],1))
      return sum(errs)/len(errs)       # MAPE
  ```
  Compare: naive(last), seasonal-naive(t−12), 3MA, blend(w) for w ∈ {0,.25,.5,.55,.6,.75,1}; choose `w` by CV and set it in config. Output `results/forecast.json`.
- **Caveat to write in docs:** data is synthetic with injected seasonality, so this validates the pipeline, not real-world accuracy.
- **STOP-GATE:** MAPE table produced; chosen `w` documented; tests cover both branches (qty given / absent).

### T1.4 Validator alignment (B-07)
- **Files:** `backend/app/validation/validator.py`, tests
- **Fix:** validate `Σx ≥ net_req` (hard), report `overshoot = Σx − net_req` as info; fail only if `overshoot > max_moq_overshoot` computed from active suppliers' MOQ. Re-check capacity, warehouse space, route cap, concentration (same predicates as solver — import shared helpers, do not duplicate).
- **Tests:** MOQ-induced overshoot passes; capacity overflow fails (`test_validator_detects_capacity_overflow` stays green); validator never triggers replan on a plan the solver proved feasible.
- **STOP-GATE:** zero spurious replans across the T1.2 200-case set.

### T1.5 Risk metric split (B-11)
- **Files:** `backend/app/agents/risk.py`, `backend/app/whatif/engine.py`, `backend/app/api/schemas.py`, tests
- **Change:** return `plan_risk` (exposure of chosen allocation) and `disruption_exposure` (active events touching used suppliers/lanes). Keep legacy `risk_score` = `plan_risk` for compatibility. In what-if diff, add both deltas plus a one-line reason string (e.g., "removed high-risk supplier").
- **STOP-GATE:** `supplier_failure` scenario shows `disruption_exposure` ↑ or an explicit explanation when `plan_risk` ↓; schema docs updated.

### T1.6 Golden diff review
- **Files:** `tests/golden/*.json`, `docs/evidence/T1.6/golden_diff.md`
- **Steps:** diff new outputs vs T0.2 goldens. Each changed field must be explained by T1.1/T1.2/T1.3. Unexplained diffs = stop.
- **STOP-GATE:** every delta justified in writing; goldens regenerated; `verify_system.py` updated with new expected values (not hard-coded old ones).

**PHASE 1 GATE (§11-P1).**

---

## 6. PHASE 2 — Agentic integrity

Goal: every LLM touchpoint is bounded, observable, and has a deterministic fallback; the LLM provably cannot change numbers.

### T2.1 LLM client contract (B-13)
- **Files:** `backend/app/llm/factory.py`, `backend/app/llm/contract.py` (new), `backend/app/graph/state.py` (trace schema), tests
- **Change:** all LLM calls go through one wrapper:
  ```python
  class LLMResult(BaseModel, Generic[T]):
      value: T
      used_llm: bool
      latency_ms: float
      fallback_reason: str | None = None

  def call_structured(schema: type[T], prompt: str, fallback: Callable[[], T],
                      *, timeout_s: float = 8, retries: int = 1) -> LLMResult[T]:
      # temperature=0; parse -> schema.model_validate; on timeout/parse/validation error -> fallback()
  ```
  Every node using it (`parse`, `supervisor`, `rag` expansion, `replan`, `explain`) appends `{node, used_llm, latency_ms, fallback_reason}` to the trace and `decision_runs.result_json`.
- **Tests:** malformed JSON → fallback used; timeout → fallback used; valid → `used_llm=True` (use a stub provider, not network).
- **STOP-GATE:** trace shows per-node `used_llm`; with provider=mock all nodes report `used_llm=false` (honest labeling — this is what lets docs say which parts were exercised).

### T2.2 Supervisor guard (B-08)
- **Files:** `backend/app/graph/nodes.py` (`supervisor_node`), tests
- **Change:**
  ```python
  REQUIRED_PROCURE = {"supplier", "route", "inventory"}
  chosen = set(llm_choice.value) & ALL_AGENTS
  agents = chosen | (REQUIRED_PROCURE if intent.kind == "procure" else set())
  ```
  Unknown agent names from the LLM are discarded and logged.
- **Tests:** LLM returns `["demand"]` for a procurement query → agents still include required set; LLM returns garbage → deterministic selection; warehouse-rebalance intent may skip route.
- **STOP-GATE:** property test — for 50 randomized LLM outputs, the solver never receives a missing-agent bundle.

### T2.3 Replan whitelist, transparency, honest claims (B-03)
- **Files:** `backend/app/graph/nodes.py` (`replan_node`), `backend/app/api/schemas.py`, `backend/app/graph/state.py`, `backend/app/validation/validator.py`, tests
- **Change:**
  ```python
  class Relaxation(BaseModel):
      constraint: Literal["lead_time", "low_risk_concentration",
                          "low_risk_reliability", "high_risk_exclusion"]
      lead_time_delta_days: conint(ge=0, le=30) = 0
      reason: str
  ```
  LLM (or deterministic fallback) may only return `list[Relaxation]` from this closed set. Apply max `settings.max_replan` rounds. Response gains:
  ```json
  "degraded": true,
  "relaxations": [{"constraint":"lead_time","lead_time_delta_days":15,"reason":"..."}]
  ```
  `degraded=true` whenever ≥1 relaxation applied. Plan status can never be plain `OPTIMAL` without the flag.
- **Docs:** delete "guaranteed feasible fallback"; replace with "if infeasible after N bounded relaxations the system returns `INFEASIBLE` with the binding constraint named".
- **Tests:** extreme demand → `INFEASIBLE` + explanation naming capacity; relaxation list is a subset of the whitelist; relaxations appear in API response and trace.
- **STOP-GATE:** no code path relaxes a constraint without emitting a `Relaxation` record.

### T2.4 Explanation faithfulness guard (B-10)
- **Files:** `backend/app/graph/nodes.py` (`explain_node`), `backend/app/graph/faithfulness.py` (new), tests
- **Change:**
  ```python
  NUM = re.compile(r"\d[\d,]*\.?\d*")
  def unfaithful_numbers(text: str, allowed: set[float], tol: float = 0.5) -> list[float]:
      nums = [float(n.replace(",", "")) for n in NUM.findall(text)]
      return [n for n in nums if not any(abs(n - a) <= tol for a in allowed)]
  # allowed = all numeric fields from solver result + counts (suppliers, routes, chunks) + run id
  ```
  If any unfaithful number → discard LLM text, use deterministic template; record `explain_fallback_reason="unfaithful_numbers"` and the offending numbers.
- **Tests:** injected LLM text with a wrong cost → fallback; correct text → kept; template itself always passes the check.
- **STOP-GATE:** faithfulness rate metric is computable from traces (feeds T4.6).

### T2.5 LLM-cannot-change-numbers invariant (B-13)
- **Files:** `backend/tests/test_llm_invariance.py` (new)
- **Test:** run the same intent through (a) mock provider, (b) a stub LLM that returns adversarial but schema-valid outputs (extra agents, odd expansions, aggressive relaxations within whitelist = none applied when plan feasible) → assert **identical** allocations & cost whenever the parsed intent is identical.
- **STOP-GATE:** invariant test passes; it is added to CI (T5.2).

**PHASE 2 GATE (§11-P2).**

---

## 7. PHASE 3 — HITL & governance hardening

### T3.1 Append-only audit events (B-09)
- **Files:** `backend/app/db/models.py`, `backend/app/db/session.py` (migration), `backend/app/db/repositories.py`, tests
- **Change:**
  ```sql
  CREATE TABLE decision_events(
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES decision_runs(id),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,            -- CREATED | APPROVE | REJECT | OVERRIDE | REPLAN | WHATIF
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
  REVOKE UPDATE, DELETE ON decision_events FROM app_user;   -- if a separate app role is used
  ```
  Repository exposes `append_event()` only (no update/delete). `hitl_*` columns on `decision_runs` become a **cached projection** of the latest event, documented as such. Wording in docs: "append-only event log" (not "immutable runs").
- **STOP-GATE:** attempting UPDATE/DELETE on events fails (test or DB privilege); every pipeline run and HITL action writes one event.

### T3.2 Authenticated reviewer identity (B-09)
- **Files:** `backend/app/api/deps.py` (new), `backend/app/api/decisions.py`, `backend/app/core/config.py`, `.env.example`, tests
- **Change:** minimal, defensible auth — API-key → planner map:
  ```python
  # PLANNER_KEYS="alice:key_a,bob:key_b"
  def current_planner(x_api_key: str = Header(...)) -> Planner:
      p = settings.planners.get(x_api_key)
      if not p: raise HTTPException(401)
      return p
  ```
  `reviewed_by` comes from the token, never from the body. Frontend sends the key from an env/config input.
- **STOP-GATE:** request without key → 401; body field `reviewed_by` ignored (test sends a forged one).

### T3.3 Meaningful `reject` (B-09)
- **Files:** `backend/app/api/decisions.py`, `backend/app/api/schemas.py`, `backend/app/whatif/engine.py` (reuse patch builder), tests
- **Change:**
  ```python
  class RejectReason(BaseModel):
      exclude_suppliers: list[str] = []
      max_supplier_share: confloat(gt=0, le=1) | None = None
      force_low_risk: bool = False
      comment: str
  ```
  Non-empty structured reason → convert to a scenario patch, re-run with `parent_run_id`, event `REJECT` + child run id. Empty structured reason → record `REJECT`, **no rerun**.
- **Tests:** reject with `exclude_suppliers=["SUP-A"]` → child run has no SUP-A allocation; reject with comment only → no new run; lineage correct.
- **STOP-GATE:** no reject path can create a run with inputs identical to the parent.

### T3.4 Full-fidelity `override` (B-09)
- **Files:** `backend/app/validation/validator.py`, `backend/app/optimization/solver.py` (`evaluate_plan`), `backend/app/api/decisions.py`, tests
- **Change:** add `evaluate_plan(allocations) -> {cost, lead_time, plan_risk, violations[]}` using the *same* cost function and the same predicates as the solver. Override accepted only if `violations == []` (MOQ, supplier cap, route cap, warehouse space, `Σ ≥ net_req`; concentration violations → allowed only with an explicit `acknowledge_policy_breach=true` + event flag). Response includes `cost_delta_vs_optimal`.
- **STOP-GATE:** one test per violation type; override with MOQ breach rejected; delta vs optimal is ≥ 0 (never "cheaper than optimal" unless constraints were breached).

### T3.5 Server-side recommendation lock + UI (B-09, B-12)
- **Files:** `backend/app/api/decisions.py`, `backend/app/api/service.py`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`
- **Change:**
  - API redacts `recommendation`/execution steps until latest event ∈ {APPROVE, OVERRIDE}; UI lock is then cosmetic over a real server rule.
  - UI: degraded banner + relaxations list (T2.3), `plan_risk` vs `disruption_exposure` (T1.5), per-node `used_llm` badges (T2.1), structured reject form (T3.3), override form with violation feedback (T3.4), event timeline from `decision_events`.
- **STOP-GATE:** `curl` on a PENDING run returns no recommendation; frontend `npm run build` clean; manual walk-through screenshot set saved to `docs/evidence/T3.5/`.

### T3.6 HITL test pack
- **Files:** `backend/tests/test_hitl.py` (new/extended)
- **Cases:** approve → event + projection; double-approve idempotent; approve after reject-child; reject variants; override variants (valid, MOQ breach, capacity breach, concentration breach ± acknowledge); 401 without key; forged `reviewed_by`; redaction while pending; lineage chain integrity.
- **STOP-GATE:** all pass; coverage of `api/decisions.py` ≥ 90% (measured, T0.4 tooling).

**PHASE 3 GATE (§11-P3).**

---

## 8. PHASE 4 — Evaluation that survives scrutiny

All outputs → `results/<name>.json` with schema:
```json
{"name":"rag","git_sha":"...","date":"...","seed":42,"n":0,
 "config":{}, "metrics":{}, "status":"OK|NOT_RUN", "notes":""}
```

### T4.1 Real embeddings & dimension consistency
- **Files:** `backend/app/rag/embed.py`, `backend/app/rag/ingest.py`, `backend/app/core/config.py`, `backend/app/db/session.py`, `scripts/reingest.sh`
- **Change:** add provider `local` using a 768-dim model (`BAAI/bge-base-en-v1.5` or `sentence-transformers/all-mpnet-base-v2`) — no API key required. Add startup assertion `assert settings.embed_dim == column_dim` (resolve 384 vs 768 per T0.3; if column is 384 → migrate and re-ingest). Mock embedder remains **for unit tests only** and is labeled.
- **STOP-GATE:** re-ingest completes; sanity test — query "safety stock policy" retrieves `inventory_safety_stock.md` in top-3 with local embeddings (this would be ~random with the mock).

### T4.2 RAG evaluation set + harness (B-04)
- **Files:** `data/eval/rag_queries.jsonl` (new), `scripts/eval_rag.py` (new), `results/rag.json`
- **Dataset rules:** ≥ 40 queries; each `{id, query, relevant_doc_ids, relevant_chunk_ids?}`; include paraphrases, SKU-code queries ("PROD-A MOQ"), and negatives (no relevant chunk). **Write queries before looking at retrieval output**; ideally a peer writes 15 of them. Corpus is 7 docs — state it; optionally add more docs/chunks (target ≥ 30 chunks).
- **Configs:** `sparse`, `dense`, `rrf`, `rrf+rerank`, each ± LLM query expansion (expansion rows `NOT_RUN` if no LLM).
- **Metrics:**
  ```python
  def mrr(ranked, rel): return next((1/i for i,d in enumerate(ranked,1) if d in rel), 0.0)
  def recall_at_k(ranked, rel, k): return len(set(ranked[:k]) & rel) / max(len(rel), 1)
  # + nDCG@k, bootstrap 95% CI (1000 resamples, seed=42)
  ```
- **STOP-GATE:** table with CI per config; conclusion allowed to be "hybrid ≈ dense" — report whatever is true.

### T4.3 Solver evaluation (B-04)
- **Files:** `scripts/eval_solver.py` (new), `results/solver.json`
- **Scenarios:** 50 seeded (demand 0.2×–3× baseline, 0–2 supplier outages, fuel 1×–2×, closed routes).
- **Baselines:** (1) greedy cheapest-landed-cost-first with capacity; (2) *optional* LLM-only allocator (real provider; `NOT_RUN` otherwise) scored for violations.
- **Metrics:** feasibility rate; **violations per plan (target 0 for solver)**; cost gap vs greedy (%); solve time p50/p95; infeasible detection correctness (compare with analytic capacity sum).
- **STOP-GATE:** solver 0 violations in all feasible cases; no "100% accuracy" wording unless computed.

### T4.4 Intent-parsing evaluation
- **Files:** `data/eval/intent_queries.jsonl` (≥ 100, labeled fields), `scripts/eval_intent.py` (rewrite `evaluate_llms.py` scope), `results/intent.json`
- **Metrics:** field-level exact-match/F1 for `product`, `quantity`, `horizon`, `low_risk`, `objective`; regex vs LLM(s); include adversarial phrasings ("10k units", "ten thousand", "ASAP but safe").
- **STOP-GATE:** per-field table; failures listed with examples.

### T4.5 Forecast evaluation consolidation
- **Files:** `scripts/eval_forecast.py` (from T1.3) → `results/forecast.json`
- **STOP-GATE:** MAPE per method, chosen weight, synthetic-data caveat embedded in `notes`.

### T4.6 Agentic ablations
- **Files:** `scripts/eval_ablation.py` (new), `results/ablation.json`
- **Rows:** (a) LLM supervisor vs rule-based; (b) LLM query expansion vs none (links to T4.2); (c) replan on vs off — recovery rate on infeasible-at-first scenarios; (d) explanation faithfulness rate (T2.4) and fallback rate; (e) end-to-end latency with real LLM vs mock (separately reported).
- **STOP-GATE:** each agentic component has a measured effect or an explicit "no measurable gain" line. Do not hide negatives.

### T4.7 One-command eval + claims register
- **Files:** `Makefile`, `scripts/build_report.py`, `docs/CLAIMS.md`, `docs/EVALUATION_REPORT.md` (generated)
- **Makefile:**
  ```make
  eval: eval-rag eval-solver eval-intent eval-forecast eval-ablation
  	python scripts/build_report.py
  eval-%:
  	python scripts/eval_$*.py --seed 42
  ```
- **CLAIMS.md rule:** every quantitative sentence in any doc → row `{claim, results file, JSON path, value}`. `build_report.py` fails if a claim's value drifts from results.
- **STOP-GATE:** `make eval` runs clean from a fresh clone; `NOT_RUN` entries are displayed, not hidden.

**PHASE 4 GATE (§11-P4).**

---

## 9. PHASE 5 — Repo hygiene & documentation

### T5.1 README, env, Makefile
- **Files:** `README.md`, `.env.example`, `Makefile`
- **Content:** 5-minute quickstart, architecture figure, modes (`mock` vs `gemini`/`local`), how to run tests/evals, known limitations.
- **STOP-GATE:** a teammate (or a clean container) reaches a working UI following only the README.

### T5.2 CI
- **Files:** `.github/workflows/ci.yml`
  ```yaml
  name: ci
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      services:
        db: {image: pgvector/pgvector:pg16, env: {POSTGRES_PASSWORD: postgres}, ports: ["5432:5432"]}
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with: {python-version: "3.11"}
        - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
        - run: cd backend && pytest --cov=app -q
        - run: cd frontend && npm ci && npm run build
  ```
- **STOP-GATE:** green on a PR; includes T2.5 invariance test and T1.2 invariants.

### T5.3 Container hardening
- **Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`
- **Change:** prod backend without `--reload`; frontend multi-stage build served by nginx; dev overrides in a separate compose file. Docs say "production-style" only if true.
- **STOP-GATE:** `docker compose up` serves the built bundle; healthchecks defined.

### T5.4 Regenerate and reconcile docs (B-05, B-12)
- **Files:** all three report docs (or replace with generated versions), `docs/ARCHITECTURE.md`
- **Rules:** resolve every T0.3 row; numbers from `results/`; test counts from pytest output; relative paths only; **remove self-assigned grade/"A+"/"100%"**; add **Limitations** (synthetic data, single-period MILP, local/mock LLM modes, small corpus, auth is demo-grade); update diagrams (solve → validate → replan/explain; LLM-touchpoint map).
- **STOP-GATE:** `grep -rn "100%\|A+\|guaranteed" docs/` returns only justified, claim-registered hits; no contradictions remain vs T0.3 table.

### T5.5 Viva / demo pack (optional, recommended)
- **Files:** `docs/VIVA_PACK.md`, `docs/DEMO_SCRIPT.md`
- **Content:** 5-minute demo path (query → plan → degraded case → HITL reject with reason → override → audit timeline); 20 likely questions with answers (why MILP vs LLM; why RRF; what "agentic" means here; what is synthetic; what failed in ablation); an honest "what was inherited vs what I built" paragraph — **written by the student**.
- **STOP-GATE:** demo script runs end-to-end in < 5 min from clean state.

---

## 10. PHASE 6 — Final audit & release

### T6.1 Full regression
```bash
docker compose down -v && docker compose up -d --build
docker compose exec backend pytest --cov=app -q | tee docs/evidence/T6.1/pytest_final.txt
python verify_system.py | tee docs/evidence/T6.1/verify_final.txt
make eval | tee docs/evidence/T6.1/eval_final.txt
cd frontend && npm run build
```
- **STOP-GATE:** all green from a cold start.

### T6.2 Final audit report
- Fill the §13.3 template; attach evidence links; list residual risks and `NOT_RUN` items.
- **STOP-GATE:** every issue B-01…B-14 has status `FIXED / MITIGATED / ACCEPTED (with reason)`.

### T6.3 Tag & freeze
- `git tag v1.0-hardened`, merge phase branches, freeze docs. Any later change requires a new log entry.

---

## 11. Phase gates (all items must be checked to proceed)

### P0 gate — baseline
- [ ] Real test count & coverage % recorded
- [ ] Goldens captured; determinism proven (empty diff)
- [ ] `AUDIT_DISCREPANCIES.md` has a resolution per row
- [ ] No code changes yet (only tooling/evidence files)

### P1 gate — correctness
- [ ] `net_requirement` tests pass (incl. `avail < SS`)
- [ ] Solver invariants: 200/200 seeded cases
- [ ] Zero spurious replans on feasible plans
- [ ] Forecast MAPE table + chosen weight documented
- [ ] Golden diff fully explained; `verify_system.py` updated
- [ ] `plan_risk` / `disruption_exposure` split live

### P2 gate — agentic integrity
- [ ] Every LLM node reports `used_llm`, `latency_ms`, `fallback_reason`
- [ ] Supervisor guard property test passes
- [ ] Every relaxation emits a `Relaxation` record; `degraded` flag present
- [ ] Explanation faithfulness guard active; fallback tested
- [ ] LLM-invariance test passes in CI

### P3 gate — governance
- [ ] `decision_events` append-only; every action logged
- [ ] Identity from token; forged `reviewed_by` ignored
- [ ] Reject cannot rerun identical inputs
- [ ] Override validated by shared predicates; delta vs optimal shown
- [ ] Recommendation redacted server-side while pending
- [ ] HITL tests pass; `api/decisions.py` coverage ≥ 90%

### P4 gate — evaluation
- [ ] Real embeddings in use; mock labeled test-only
- [ ] RAG: ≥ 40 queries, CIs, honest conclusion
- [ ] Solver: 50 scenarios, greedy baseline, 0 violations
- [ ] Intent: ≥ 100 labeled queries, per-field F1
- [ ] Ablations incl. negatives
- [ ] `make eval` from clean clone; `CLAIMS.md` complete

### P5 gate — hygiene
- [ ] README quickstart verified by someone else
- [ ] CI green
- [ ] Prod-style containers (no `--reload`, built frontend)
- [ ] Docs reconciled; no unregistered quantitative claims; limitations section present

### P6 gate — release
- [ ] Cold-start regression green
- [ ] Final audit report complete; B-01…B-14 all dispositioned
- [ ] Tag created

---

## 12. Module audit matrix (fill after each task — R12)

**Per-module audit procedure (apply to every row):**
1. **Diff review** — only intended lines changed; no dead code; no TODOs left.
2. **Invariants** — listed invariants still hold (test or assertion exists).
3. **Tests** — new tests added for each behavior change; names reference the issue ID.
4. **Perf** — latency within 2× baseline (record p50/p95).
5. **Docs** — module description, diagram, and CLAIMS.md updated.
6. **Sign-off** — reviewer initials + date.

| Module | Tasks | Key invariants | Required checks | Status |
|---|---|---|---|---|
| `agents/inventory.py` | T1.1 | `net = max(0, D + SS − avail)`; avail uses `max(0, on_hand − reserved)` | 4 unit tests; golden diff | [ ] |
| `agents/demand.py` | T1.3 | forecast never overrides explicit qty; weights from config | MAPE table; branch tests | [ ] |
| `agents/supplier.py` | T1.2 (inputs), T3.3 | excluded suppliers never reach solver | what-if exclusion tests | [ ] |
| `agents/route.py` | T1.2 | closed route ⇒ capacity 0; fuel multiplier applied once | route-closure test | [ ] |
| `agents/risk.py` | T1.5 | `plan_risk` ∈ [0,100]; `disruption_exposure` separate | scenario semantics test | [ ] |
| `optimization/solver.py` | T1.2, T3.4 | all constraints linear; `y_s` binary; infeasible ⇒ INFEASIBLE | 200-case invariants; `evaluate_plan` parity | [ ] |
| `validation/validator.py` | T1.4, T3.4 | same predicates as solver (shared); no spurious replan | spurious-replan sweep | [ ] |
| `graph/nodes.py` | T1.3, T2.2, T2.3, T2.4 | required agents always run; relaxations whitelisted; explanation faithful | supervisor property test; relax tests; faithfulness tests | [ ] |
| `graph/graph.py` | T2.3 | replan count ≤ `max_replan`; edge order = docs | graph-structure test | [ ] |
| `graph/state.py` | T2.1 | trace carries `used_llm` per node | schema test | [ ] |
| `llm/factory.py`, `llm/contract.py` | T2.1 | temperature 0; schema-validated; fallback always available | stub-provider tests | [ ] |
| `rag/embed.py`, `ingest.py`, `search.py` | T4.1, T4.2 | embed dim == column dim (asserted); mock = tests only | sanity retrieval; eval harness | [ ] |
| `whatif/engine.py` | T1.5, T3.3 | patches don't mutate master data; diff includes both risk metrics | all-6-scenario test; reject→patch test | [ ] |
| `api/decisions.py`, `api/service.py` | T3.1–T3.5 | identity from token; redaction while pending; every action → event | HITL pack (T3.6) | [ ] |
| `api/schemas.py` | T1.5, T2.3, T3.3 | `degraded`, `relaxations`, `plan_risk`, `disruption_exposure` present | schema snapshot test | [ ] |
| `db/models.py`, `db/session.py` | T3.1, T4.1 | `decision_events` append-only; vector dim consistent | migration test on fresh DB | [ ] |
| `frontend/src/App.tsx`, `api/client.ts` | T3.5 | UI reflects server truth (banner, lock, timeline) | `npm run build`; walkthrough evidence | [ ] |
| `scripts/*` | T0.2, T1.3, T4.* | seed=42; write `results/*.json` | `make eval` clean | [ ] |
| `docker-compose.yml`, Dockerfiles | T5.3 | no `--reload`; built frontend | cold-start run | [ ] |
| `.github/workflows/ci.yml` | T5.2 | runs invariants + invariance + build | green PR | [ ] |
| `docs/*` | T5.4 | numbers only from `results/`; no contradictions | grep audit; CLAIMS drift check | [ ] |

---

## 13. Templates

### 13.1 `docs/EXECUTION_LOG.md` entry
```markdown
## T1.1 — Fix net requirement
- Date/Agent: 2026-10-__ / <agent>
- Branch/Commit: fix/p1-correctness @ <sha>
- VERIFY findings: <what the code actually looked like>
- DECISION NEEDED: <none | question → chosen option + who decided>
- Tests added: test_inventory.py::{...}
- Tests changed (R3 justification): <file::name — encoded bug B-01 (expected 9470)>
- Gate G0: pytest <N passed> · verify_system 5/5 · diff stat: <files>
- Evidence: docs/evidence/T1.1/
- Module audit row updated: yes/no
- Issues dispositioned: B-01 FIXED
- Notes / follow-ups:
```

### 13.2 Agent kickoff prompt (paste to the executor agent)
```text
You are executing docs/SupplyChainAI_FIX_AND_EXECUTION_PLAN.md on the repo at ./Agentic_AI-main.
Follow §2 rules R1–R12 exactly. Work tasks in the order of §3. For each task:
1) VERIFY in code; 2) write failing tests (bug tasks); 3) implement within the task's Files list;
4) run Gate G0; 5) save evidence to docs/evidence/<task>/; 6) append the §13.1 log entry;
7) update the §12 module row; 8) commit "<TaskID>: <summary>".
STOP and report on any §2 stop condition. For "DECISION NEEDED", write the question, options and your
recommendation to the log, skip that task, and continue with independent tasks.
Never invent metrics, never weaken tests, never let LLM output set numbers.
After each PHASE, run the phase gate checklist in §11 and print it with checked/unchecked items.
Do not start the next phase until the gate is fully checked or the human waives an item in writing.
```

### 13.3 Final audit report skeleton (`docs/FINAL_AUDIT.md`)
```markdown
# Final Audit — SupplyChainAI v1.0-hardened
## Issue disposition
| ID | Status (FIXED/MITIGATED/ACCEPTED) | Evidence | Notes |
## Metrics (from results/, with CI where applicable)
## Test & coverage summary (real numbers)
## Agentic components: measured effect (incl. negatives)
## Residual risks & limitations
## NOT_RUN items and why
## Sign-off: <name/date>
```

---

## 14. Risk register & assumptions

| Risk | Impact | Mitigation |
|---|---|---|
| Docs ≠ code (code not inspected here) | Wrong fixes | Every task starts with VERIFY; T0.3 resolves truth |
| Net-req fix makes Product A infeasible | Demo breaks | Expected; record in T1.6; use it as the showcase for honest `INFEASIBLE` + HITL path; adjust *demo data* only via seed with documented reason |
| No LLM API key / quota | Phase 4 LLM rows empty | Use local model if feasible; otherwise `NOT_RUN` and say so |
| Embedding dim migration | Re-ingest needed | T4.1 assertion + `reingest.sh` |
| Time pressure | Incomplete | Use minimum path below |
| Inherited base project (docs say "already present vs added") | Viva exposure | T5.5 student-written provenance paragraph; log which modules you personally changed |

**Assumptions:** PostgreSQL 16 + pgvector stays; LangGraph + OR-Tools stay; synthetic data stays (disclosed); single-period MILP stays (multi-period MPC is future work, not in scope).

---

## 15. Timeline

| Phase | Effort | Cumulative |
|---|---|---|
| P0 baseline | 0.5 d | 0.5 d |
| P1 correctness | 1.5 d | 2 d |
| P2 agentic integrity | 1.5 d | 3.5 d |
| P3 governance | 2 d | 5.5 d |
| P4 evaluation | 3 d | 8.5 d |
| P5 hygiene | 0.5–1 d | ~9.5 d |
| P6 release | 0.5 d | ~10 d |

**Minimum viable path (≈ 5 days) if time-boxed:** T0.1–T0.4 → T1.1, T1.2, T1.4, T1.6 → T2.1, T2.3 → T4.1, T4.2, T4.3 → T5.4 → T6.1–T6.3. Everything skipped must be listed under *Limitations* with the reason.

---

## 16. Definition of done

- Every issue B-01…B-14 dispositioned with evidence.
- Zero numeric decisions by the LLM, **proven** by T2.5 and solver invariants.
- Every number in the docs traces to `results/*.json` via `docs/CLAIMS.md`.
- Every relaxation, override, rejection, and approval is visible in API, UI, and the append-only event log.
- Cold-start `docker compose up` + `make eval` + `pytest` green; README reproduces it.
