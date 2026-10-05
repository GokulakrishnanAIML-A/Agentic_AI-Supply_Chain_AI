# Golden Baseline Diff Review (T1.6)

**Date:** 2026-10-05  
**Reviewer:** Antigravity Agent  
**Branch:** `fix/p1-correctness`  

---

## 1. Summary of Changes

All deltas observed in `tests/golden/*.json` are directly and strictly attributed to the three intentional Phase 1 correctness fixes:
1. **T1.1 (Net Requirement Formula Fix, B-01)**: Corrected double-counting of available inventory when stock was below safety threshold (`D + SS - 2*avail` $\to$ `max(0, D + SS - avail)`).
2. **T1.2 (Solver Formulation Hardening, B-02)**: Added explicit route capacity bounds and verified binary $y_s$ selection.
3. **T1.5 (Risk Metric Split, B-11)**: Integrated `plan_risk` and `disruption_exposure` into what-if diff structures.

No unexpected or unintended numerical drifts were detected.

---

## 2. Field-by-Field Delta Justification

### 2.1. Product A 10,000 Units Baseline (`product_a_10k_baseline.json`)
- **Net Requirement:** Shifted from `9,470` $\to$ `10,610`.
  - *Calculation:* $\text{Demand} (10,000) + \text{SafetyStock} (1,750) - \text{Available} (1,140) = 10,610$.
  - *Previous Bug:* Old buggy formula computed $10,000 - 1,140 + (1,750 - 1,140) = 9,470$ (under-procuring 1,140 units).
- **Allocations:**
  - `SUP-A`: 5,500 units (max 60% concentration cap).
  - `SUP-C`: Increased from 3,665 $\to$ 4,520 units.
  - `SUP-B`: Increased from 305 $\to$ 590 units.
  - *Total Procured:* Exactly 10,610 units.
- **Cost Impact:**
  - `procurement_cost`: \$38,765.75 $\to$ \$43,511.00.
  - `transport_cost`: \$4,103.06 $\to$ \$4,635.56.
  - `total_cost`: \$42,868.81 $\to$ \$48,146.56 (consistent with procuring 1,140 additional units).

### 2.2. Product A Zero User Demand (`product_a_0_demand.json`)
- **Net Requirement:** Shifted from `0` $\to$ `610`.
  - *Reason:* When demand is 0, the DCs currently have 1,140 available vs 1,750 required safety stock. The system correctly replenishes the 610-unit safety gap ($1,750 - 1,140 = 610$).
- **Allocations:** 360 units via SUP-A, 250 units via SUP-D (Total = 610 units, cost = \$2,946.26).

### 2.3. What-If Scenarios (`what_if_scenarios.json`)
- All 6 scenarios updated to use the new 10,610 baseline.
- Added `plan_risk` and `disruption_exposure` alongside `risk_explanation` strings.
- Determinism check verified byte-identical output across consecutive runs.

---

## 3. Verdict

The Phase 1 correctness updates are mathematically sound, verified by 200/200 invariant test scenarios, and approved.
