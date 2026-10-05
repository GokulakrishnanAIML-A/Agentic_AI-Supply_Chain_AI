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




