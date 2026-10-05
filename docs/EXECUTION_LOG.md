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
