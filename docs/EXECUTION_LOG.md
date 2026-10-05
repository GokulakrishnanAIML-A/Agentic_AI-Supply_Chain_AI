# SupplyChainAI — Execution Log

Living log of all task executions following `SupplyChainAI_FIX_AND_EXECUTION_PLAN.md` §2 rules (R1–R12).

---

## T0.1 — Environment & branch setup
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p0-baseline` @ `1bf7694`
- **VERIFY findings:**
  - Python version: 3.13.7
  - Docker version: 28.4.0
  - Test suite size: 23 collected tests across `test_pipeline.py` (8), `test_api.py` (4), and `test_extended_verification.py` (11).
  - Without external Postgres running, 14 unit/pipeline tests pass and 9 API client tests are gracefully skipped by `conftest.py`.
- **DECISION NEEDED:** None.
- **Tests added:** None (baseline freeze).
- **Tests changed:** None.
- **Gate G0:** pytest 14 passed / 9 skipped (23 collected) · diff stat matches expected baseline evidence.
- **Evidence:** `docs/evidence/T0.1/pip_freeze.txt`, `docs/evidence/T0.1/pytest_baseline.txt`
- **Module audit row updated:** Initialized §12.
- **Issues dispositioned:** Baseline environment established.
- **Notes / follow-ups:** Ready for T0.2 (Golden baseline capture) and T0.3 (Discrepancy audit against code).

---

## T0.2 — Golden baseline capture
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p0-baseline`
- **VERIFY findings:** Captured deterministic solver runs across 3 baseline scenarios (Product A 10k baseline, SUP-C failure, zero-demand) plus all 6 What-If scenario patches into `tests/golden/*.json`.
- **DECISION NEEDED:** None.
- **Tests added:** `scripts/capture_golden.py`
- **Tests changed:** None.
- **Gate G0:** Re-running capture twice yields byte-identical output across all golden JSON files.
- **Evidence:** `docs/evidence/T0.2/determinism_diff.txt` ("EMPTY DIFF — Byte-identical output across runs (determinism proven).")
- **Module audit row updated:** Yes.
- **Issues dispositioned:** Golden baseline frozen for regression monitoring.

---

## T0.3 — Discrepancy audit against code
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p0-baseline`
- **VERIFY findings:** All 9 cross-document contradiction items audited against physical codebase:
  1. Vector dimension is 768 (`models.py:226`, `config.py:21`).
  2. RRF uses equal weights ($k=60$) + lexical overlap rerank (`search.py:54-66`).
  3. Sparse query uses `plainto_tsquery` and `ts_rank` (`search.py:41-47`).
  4. Demand forecast blend is 55% seasonal naive / 45% 3-month moving average (`demand.py:20`).
  5. Low-risk sourcing rules: reliability $\ge 0.90$, high-risk $\le 15\%$, single-vendor $\le 60\%$ (`solver.py:145-163`).
  6. MILP variables include integer $x_{s,r}$ and binary $y_s$ BoolVar for MOQ (`solver.py:117-127`).
  7. Warehouse inbound remaining space constraint is active in solver (`solver.py:130-142`).
  8. Test suite count is exactly 23 items (`backend/tests/`).
  9. State graph edge order is `specialists` $\to$ `solve` $\to$ `validate` $\to$ `replan`/`explain` (`graph.py:37-45`).
- **DECISION NEEDED:** None (all resolved by code truth).
- **Tests added:** None.
- **Tests changed:** None.
- **Gate G0:** `docs/AUDIT_DISCREPANCIES.md` generated with complete resolutions for every row.
- **Evidence:** `docs/AUDIT_DISCREPANCIES.md`
- **Module audit row updated:** Yes.
- **Issues dispositioned:** B-05 Ground truth established.

---

## T0.4 — Coverage baseline
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p0-baseline`
- **VERIFY findings:** Measured code coverage using `pytest-cov` on unit/pipeline test execution.
- **Results:**
  - Total Statements: 1369
  - Missed Statements: 687
  - Baseline Coverage: **50%** (with mock DB; solver at 92%, what-if at 98%, models at 100%).
- **DECISION NEEDED:** None.
- **Tests added:** `backend/requirements-dev.txt`
- **Tests changed:** None.
- **Gate G0:** Real coverage percentage recorded, replacing legacy unmeasured claims.
- **Evidence:** `docs/evidence/T0.4/coverage.txt`
- **Module audit row updated:** Yes.
- **Issues dispositioned:** B-14 baseline measured.

---

## PHASE 0 GATE SUMMARY: PASSED ✅
- [x] Real test count (23 items) & coverage % (50% unit baseline) recorded.
- [x] Goldens captured; determinism proven (empty diff).
- [x] `AUDIT_DISCREPANCIES.md` has a resolution per row (9/9 items).
- [x] No code changes yet (tooling, golden files, and evidence only).

---

## T1.1 — Fix net requirement (B-01)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Located double-counting bug in `backend/app/agents/inventory.py` lines 34–35 where `safety_gap = max(0, total_ss - total_available)` was added to `demand - total_available`, producing `D + SS - 2*avail` when `avail < SS`.
- **DECISION NEEDED:** Policy = safety stock must be fully replenished after serving demand (implemented).
- **Tests added:** `backend/tests/test_inventory.py::{test_no_double_count, test_surplus_is_zero, test_ss_topup, test_zero_everything}`
- **Tests changed (R3 justification):** `backend/tests/conftest.py` lines 106–107 updated to use the exact same pure `net_requirement` formula `max(0, demand + total_ss - total_available)`.
- **Gate G0:** pytest 18 passed / 9 skipped (27 collected) · diff stat restricted to inventory.py, conftest.py, and test_inventory.py.
- **Evidence:** `docs/evidence/T1.1/test_inventory_output.txt`, `docs/evidence/T1.1/git_diff_stat.txt`
- **Module audit row updated:** `agents/inventory.py` invariant verified.
- **Issues dispositioned:** B-01 FIXED.
- **Notes / follow-ups:** Proceed to T1.2 (Solver formulation audit and invariant testing).

---

## T1.2 — Solver formulation audit & invariant testing (B-02)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Audited MILP formulation in `backend/app/optimization/solver.py`. Confirmed binary selection indicators `y[s] = BoolVar()`, linear Big-M bounds on monthly capacity and MOQ, warehouse inbound remaining space constraints, and added explicit route capacity constraints.
- **DECISION NEEDED:** None (formulation verified and tightened).
- **Tests added:** `backend/tests/test_solver_invariants.py::test_200_seeded_solver_invariants` (200 seeded random scenarios with randomized demand, supplier outages, route disruptions, and economic multipliers).
- **Tests changed:** None.
- **Gate G0:** 200/200 invariant scenarios passed in 1.76s (p95 solve time < 20ms) · all 6 invariants verified.
- **Evidence:** `docs/evidence/T1.2/solver_invariants_output.txt`, `docs/evidence/T1.2/git_diff_stat.txt`
- **Module audit row updated:** `optimization/solver.py` invariant verified.
- **Issues dispositioned:** B-02 FIXED.
- **Notes / follow-ups:** Proceed to T1.3 (Demand forecast validation & holdout evaluation).

---

## T1.3 — Forecast validation & holdout evaluation (B-06)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Validated `backend/app/agents/demand.py`. When user specifies a quantity, that quantity is used as `demand_to_meet`, and a notice is appended if user demand differs by $>25\%$ from statistical forecast. Implemented rolling-origin cross-validation ($h=1, \text{min\_train}=12$) in `scripts/eval_forecast.py` evaluating 8 models across historical orders.
- **DECISION NEEDED:** Retain active 55% seasonal naive / 45% 3MA blend (achieved 6.49% MAPE on synthetic seasonal series).
- **Tests added:** `backend/tests/test_forecast.py::{test_seasonal_forecast_with_full_history, test_forecast_short_history, test_forecast_empty_history}`, `scripts/eval_forecast.py`.
- **Tests changed:** None.
- **Gate G0:** 3/3 forecast tests passed · `results/forecast.json` generated with full MAPE benchmark table.
- **Evidence:** `docs/evidence/T1.3/forecast_tests_output.txt`, `docs/evidence/T1.3/git_diff_stat.txt`, `results/forecast.json`
- **Module audit row updated:** `agents/demand.py` invariant verified.
- **Issues dispositioned:** B-06 FIXED.
- **Notes / follow-ups:** Proceed to T1.4 (Validator alignment).

---

## T1.4 — Validator alignment (B-07)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Updated `backend/app/validation/validator.py` `validate_plan` function with shared solver predicates: exact demand fulfillment check, supplier capacity and MOQ violation checks, warehouse remaining capacity check, and reporting `overshoot = max(0, filled - net_req)`.
- **DECISION NEEDED:** None.
- **Tests added:** None (validator exercised across full suite and invariants).
- **Tests changed:** None.
- **Gate G0:** 22 unit tests passed / 9 DB tests skipped (31 collected) · zero spurious replans on solver-feasible plans.
- **Evidence:** `docs/evidence/T1.4/validator_tests_output.txt`, `docs/evidence/T1.4/git_diff_stat.txt`
- **Module audit row updated:** `validation/validator.py` invariant verified.
- **Issues dispositioned:** B-07 FIXED.
- **Notes / follow-ups:** Proceed to T1.5 (Risk metric split).

---

## T1.5 — Risk metric split (B-11)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Investigated scenario where excluding low-reliability suppliers shifted mean supplier reliability. Added `plan_risk` (selected supplier risk exposure) and `disruption_exposure` (external incident severity) to `RiskResult` schema, and added contextual explanatory notes to what-if diff results.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_extended_verification.py::test_whatif_diff_results` verifies presence and semantics of split metrics.
- **Tests changed:** None.
- **Gate G0:** 22 unit tests passed / 9 DB tests skipped (31 collected) · diff stat restricted to risk.py, schemas.py, engine.py.
- **Evidence:** `docs/evidence/T1.5/risk_tests_output.txt`, `docs/evidence/T1.5/git_diff_stat.txt`
- **Module audit row updated:** `agents/risk.py` invariant verified.
- **Issues dispositioned:** B-11 FIXED.
- **Notes / follow-ups:** Proceed to T1.6 (Golden diff review and Phase 1 gate).

---

## T1.6 — Golden diff review & Phase 1 Gate
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p1-correctness`
- **VERIFY findings:** Diffed new solver outputs against T0.2 baseline. All deltas strictly traceable to:
  1. T1.1: Net requirement shift from 9,470 $\to$ 10,610 (restoring safety stock replenishment).
  2. T1.2: Addition of explicit route capacity constraints.
  3. T1.5: Split risk metrics `plan_risk` and `disruption_exposure`.
- **DECISION NEEDED:** None.
- **Tests added:** None.
- **Tests changed:** Regenerated `tests/golden/*.json`.
- **Gate G0:** All 22 unit tests passed / 9 DB tests skipped · determinism check passed with byte-identical runs.
- **Evidence:** `docs/evidence/T1.6/golden_diff.md`, `docs/evidence/T1.6/golden_raw_diff.txt`
- **Module audit row updated:** Phase 1 complete.
- **Issues dispositioned:** Golden baselines reconciled with verified mathematical formulas.

---

## PHASE 1 GATE SUMMARY: PASSED ✅
- [x] `net_requirement` tests pass (including `avail < SS` replenishment).
- [x] Solver invariants: 200/200 seeded random cases pass.
- [x] Zero spurious replans on solver-feasible plans.
- [x] Forecast MAPE table (6.49% for active 55/45 blend) + synthetic data caveat documented.
- [x] Golden diff fully justified in writing in `docs/evidence/T1.6/golden_diff.md`.
- [x] `plan_risk` and `disruption_exposure` metric split live in schemas, agents, and what-if diff.

---

## T2.1 — LLM client contract & observability (B-13)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p2-agentic`
- **VERIFY findings:** Built standardized wrapper `call_structured()` in `backend/app/llm/contract.py`. Captures `used_llm`, `latency_ms`, and `fallback_reason` across every LangGraph node (`parse`, `supervisor`, `rag`, `replan`, `explain`).
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_agentic_integrity.py`
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T2/agentic_tests_output.txt`
- **Module audit row updated:** `llm/contract.py`, `graph/state.py` verified.
- **Issues dispositioned:** B-13 FIXED.

---

## T2.2 — Supervisor guard (B-08)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p2-agentic`
- **VERIFY findings:** Implemented hard supervisor guard in `backend/app/graph/nodes.py`. When a procurement query is processed, `REQUIRED_PROCURE = {"demand", "supplier", "route", "inventory", "risk"}` is guaranteed present in the execution set regardless of LLM omissions or malformed outputs.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_agentic_integrity.py::test_supervisor_guard_property` (50 randomized/adversarial LLM choice tests).
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T2/agentic_tests_output.txt`
- **Module audit row updated:** `graph/nodes.py` verified.
- **Issues dispositioned:** B-08 FIXED.

---

## T2.3 — Replan whitelist & transparency (B-03)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p2-agentic`
- **VERIFY findings:** Replaced unbounded replanning with explicit `Relaxation` schema restricted to closed set (`lead_time`, `low_risk_concentration`, `low_risk_reliability`, `high_risk_exclusion`). Stamped `degraded=True` and appended full relaxation list in state.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_agentic_integrity.py::test_replan_whitelist_and_degraded_flag`.
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T2/agentic_tests_output.txt`
- **Module audit row updated:** `graph/nodes.py` verified.
- **Issues dispositioned:** B-03 FIXED.

---

## T2.4 — Explanation faithfulness guard (B-10)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p2-agentic`
- **VERIFY findings:** Created `backend/app/graph/faithfulness.py`. Checks all extracted numbers from generated explanations against known ground truth facts from OR-Tools solver outputs, entity counts, and demand/risk numbers.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_agentic_integrity.py::test_explanation_faithfulness_guard`.
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T2/agentic_tests_output.txt`
- **Module audit row updated:** `graph/faithfulness.py` verified.
- **Issues dispositioned:** B-10 FIXED.

---

## T2.5 — LLM mathematical invariance test (B-13)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p2-agentic`
- **VERIFY findings:** Proved that solver allocations, unit quantities, line costs, and objective totals are strictly invariant to LLM non-determinism.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_llm_invariance.py::test_llm_cannot_change_solver_numbers`.
- **Tests changed:** None.
- **Gate G0:** Invariance test passed in CI suite.
- **Evidence:** `docs/evidence/T2/agentic_tests_output.txt`
- **Module audit row updated:** Phase 2 complete.
- **Issues dispositioned:** B-13 Invariant proven.

---

## PHASE 2 GATE SUMMARY: PASSED ✅
- [x] Every LLM node reports `used_llm`, `latency_ms`, and `fallback_reason`.
- [x] Supervisor guard property test passes across 50 randomized cases.
- [x] Every relaxation emits a `Relaxation` record from the closed whitelist; `degraded=True` tagged.
- [x] Explanation faithfulness guard active and tested.
- [x] LLM-cannot-change-numbers mathematical invariance test passing.

---

## T3.1 — Append-only audit events (B-09)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** Created `decision_events` table in `backend/app/db/models.py` with foreign key to `decision_runs.id`, `actor`, `action` (CREATED | APPROVE | REJECT | OVERRIDE | REPLAN | WHATIF), `payload` (JSONB), and `created_at` (TIMESTAMPTZ). Exposed `append_event()` and `get_events_for_run()` in `backend/app/db/repositories.py`. Maintained `hitl_*` columns on `decision_runs` as a cached projection of the latest audit event.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_hitl.py::test_append_event_and_history`.
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`, `docs/evidence/T3/git_diff_stat.txt`
- **Module audit row updated:** `db/models.py`, `db/repositories.py` verified.
- **Issues dispositioned:** B-09 append-only audit event logging implemented.

---

## T3.2 — Authenticated reviewer identity (B-09)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** Implemented `current_planner` dependency in `backend/app/api/deps.py` extracting reviewer identity from `X-API-Key` mapped via `settings.planners`. Updated `.env.example` and `Settings.planner_keys`. Request without valid key raises 401; request body field `planner_name` is ignored in favor of token.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_hitl.py::test_current_planner_auth`.
- **Tests changed:** None.
- **Gate G0:** Passed (401 on missing or invalid key).
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`
- **Module audit row updated:** `api/deps.py`, `core/config.py` verified.
- **Issues dispositioned:** B-09 reviewer authentication implemented.

---

## T3.3 — Meaningful reject handling (B-09)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** Updated `backend/app/api/decisions.py` and `backend/app/api/schemas.py`. Defined `RejectReason` (with `exclude_suppliers`, `max_supplier_share`, `force_low_risk`, `comment`). When structured constraints are provided, triggers re-optimization with child run linked via `parent_run_id` and records `REJECT` event. When comment-only, records `REJECT` event without re-running.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_hitl.py::test_reject_comment_only`.
- **Tests changed:** None.
- **Gate G0:** Passed.
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`
- **Module audit row updated:** `api/decisions.py`, `api/schemas.py` verified.
- **Issues dispositioned:** B-09 meaningful reject handling implemented.

---

## T3.4 — Full-fidelity override validation (B-09)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** Added `evaluate_plan()` to `backend/app/optimization/solver.py` and updated `backend/app/validation/validator.py`. Validates MOQ, supplier monthly capacity, warehouse remaining space, and concentration policy limits. Policy breaches require `acknowledge_policy_breach=True`. Calculates `cost_delta_vs_optimal` ($\ge 0$).
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_hitl.py::{test_override_valid, test_override_moq_breach_rejected, test_override_capacity_breach_rejected, test_override_concentration_breach_policy}`.
- **Tests changed:** None.
- **Gate G0:** Passed (all violation and acknowledgment scenarios verified).
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`
- **Module audit row updated:** `optimization/solver.py`, `validation/validator.py` verified.
- **Issues dispositioned:** B-09 full-fidelity override validation implemented.

---

## T3.5 — Server-side recommendation lock & UI hardening (B-09, B-12)
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** In `backend/app/api/service.py`, enforced server-side recommendation lock: downstream execution steps and PO plans are redacted/stamped `[LOCKED]` while `hitl_status == 'PENDING_REVIEW'`. Updated `frontend/src/App.tsx` and `frontend/src/api/client.ts` with degraded mode banner, split risk metrics, node badges, structured reject drawer, manual override editor with real-time feedback, and audit events timeline.
- **DECISION NEEDED:** None.
- **Tests added:** `backend/tests/test_hitl.py::test_server_side_recommendation_lock`, frontend `npm run build` test.
- **Tests changed:** None.
- **Gate G0:** Passed (clean `vite build` production bundle generated in 1.6s).
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`, `docs/evidence/T3/git_diff_stat.txt`
- **Module audit row updated:** `api/service.py`, `frontend/src/App.tsx` verified.
- **Issues dispositioned:** B-09 and B-12 recommendation lock and UI verified.

---

## T3.6 — HITL test pack & coverage gate
- **Date/Agent:** 2026-10-05 / Antigravity Agent
- **Branch/Commit:** `fix/p3-governance`
- **VERIFY findings:** Built comprehensive test suite covering all 9 HITL governance paths in `backend/tests/test_hitl.py`. Total test suite reached 35 passed unit/invariant/HITL tests with 72% overall statement coverage.
- **DECISION NEEDED:** None.
- **Tests added:** 9 test cases in `backend/tests/test_hitl.py`.
- **Tests changed:** None.
- **Gate G0:** 9/9 HITL tests passed in 1.44s · total suite 35/35 passed in 16.18s · 72% coverage.
- **Evidence:** `docs/evidence/T3/hitl_tests_output.txt`
- **Module audit row updated:** Phase 3 complete.
- **Issues dispositioned:** Phase 3 governance and audit requirements fulfilled.

---

## PHASE 3 GATE SUMMARY: PASSED ✅
- [x] `decision_events` append-only audit table and repository functions active.
- [x] Reviewer authentication via `X-API-Key` enforced; forged body names ignored.
- [x] Meaningful reject with structured scenario patches re-runs; comment-only logs without re-run.
- [x] Full-fidelity manual override evaluates exact solver predicates and reports `cost_delta_vs_optimal`.
- [x] Server-side recommendation lock redacts execution plan until approved; frontend UI updated and builds cleanly (`vite build` 0 errors).
- [x] 9/9 HITL test suite cases pass; test suite coverage increased to 72%.








