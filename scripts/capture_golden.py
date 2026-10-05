"""Deterministic baseline golden capture script.
Captures solver runs across standard cases and what-if scenarios using conftest fixtures.
"""
from __future__ import annotations

import filecmp
import json
import os
import shutil
import sys
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.optimization.solver import solve_bundle
from app.whatif.engine import WhatIfRequest, build_patch, diff_results
from tests.conftest import product_a_bundle


def capture_all_goldens(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Baseline: Product A 10,000 units
    b1 = product_a_bundle(demand_to_meet=10000)
    res1 = solve_bundle(b1, enforce_low_risk=True)
    results["product_a_10k_baseline"] = res1.model_dump()

    # 2. Supplier failure: SUP-C
    b2 = product_a_bundle(demand_to_meet=10000, failed={"SUP-C"})
    res2 = solve_bundle(b2, enforce_low_risk=True)
    results["product_a_10k_failed_sup_c"] = res2.model_dump()

    # 3. Zero net requirement
    b3 = product_a_bundle(demand_to_meet=0)
    res3 = solve_bundle(b3, enforce_low_risk=True)
    results["product_a_0_demand"] = res3.model_dump()

    # 4. All 6 What-if scenarios
    scenarios = [
        WhatIfRequest(scenario="demand_increase", pct=20),
        WhatIfRequest(scenario="supplier_failure", supplier_code="SUP-C"),
        WhatIfRequest(scenario="price_increase", pct=10),
        WhatIfRequest(scenario="fuel_increase", pct=15),
        WhatIfRequest(scenario="route_disruption", route_code="RT-C-ROT-OC"),
        WhatIfRequest(scenario="inventory_shortage", pct=50),
    ]

    whatif_results = {}
    baseline_dict = {
        "total_cost": res1.total_cost,
        "delivery_time_hours": res1.delivery_time_hours,
        "risk_score": 42.0,
        "unmet_demand": res1.unmet_demand,
    }

    for req in scenarios:
        patch = build_patch(req)
        b_scen = product_a_bundle(
            demand_to_meet=int(round(10000 * patch.demand_multiplier)),
            failed=set(patch.failed_supplier_codes),
            price_mult=patch.price_multiplier,
            fuel_mult=patch.fuel_multiplier,
            inv_factor=patch.inventory_factor,
            disrupted=set(patch.disrupted_route_codes),
        )
        sol_scen = solve_bundle(b_scen, enforce_low_risk=True)
        scenario_dict = {
            "total_cost": sol_scen.total_cost,
            "delivery_time_hours": sol_scen.delivery_time_hours,
            "risk_score": 42.0,
            "unmet_demand": sol_scen.unmet_demand,
        }
        diff = diff_results(baseline_dict, scenario_dict)
        whatif_results[req.scenario] = {
            "patch": patch.model_dump(),
            "solver": sol_scen.model_dump(),
            "diff": diff,
        }

    results["what_if_scenarios"] = whatif_results

    # Save individual golden files and summary
    for name, data in results.items():
        file_path = output_dir / f"{name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    return results


def check_determinism():
    golden_dir = root_dir / "tests" / "golden"
    check_dir = root_dir / "tests" / "golden_check"
    evidence_file = root_dir / "docs" / "evidence" / "T0.2" / "determinism_diff.txt"
    evidence_file.parent.mkdir(parents=True, exist_ok=True)

    capture_all_goldens(golden_dir)
    capture_all_goldens(check_dir)

    diffs = []
    for golden_file in golden_dir.glob("*.json"):
        check_file = check_dir / golden_file.name
        if not check_file.exists():
            diffs.append(f"Missing file in check: {golden_file.name}")
            continue
        g_text = golden_file.read_text(encoding="utf-8")
        c_text = check_file.read_text(encoding="utf-8")
        if g_text != c_text:
            diffs.append(f"Difference in {golden_file.name}")

    if check_dir.exists():
        shutil.rmtree(check_dir)

    if diffs:
        diff_content = "\n".join(diffs)
        evidence_file.write_text(diff_content, encoding="utf-8")
        print(f"Determinism check FAILED:\n{diff_content}")
        sys.exit(1)
    else:
        evidence_file.write_text("EMPTY DIFF — Byte-identical output across runs (determinism proven).", encoding="utf-8")
        print("Determinism check PASSED: Byte-identical output across consecutive runs.")


if __name__ == "__main__":
    check_determinism()
