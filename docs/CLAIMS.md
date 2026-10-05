# Quantitative Claims Register

All numbers reported in this project are empirically measured and traced to benchmark artifacts in `results/*.json`.
The automated report generator `scripts/build_report.py` audits this register on every evaluation pass.

| Claim ID | Claim Description | Results File | JSON Path | Expected Value | Status |
|---|---|---|---|---|---|
| C-01 | OR-Tools MILP guarantees zero hard constraint violations | `results/solver.json` | `metrics.solver_hard_violations_per_plan` | `0.0` | VERIFIED ✅ |
| C-02 | Infeasible scenario detection accuracy is 100% | `results/solver.json` | `metrics.infeasible_detection_accuracy` | `1.0` | VERIFIED ✅ |
| C-03 | Solver median solve time (p50) is under 20ms | `results/solver.json` | `metrics.solve_time_ms_p50` | `< 20.0` | VERIFIED ✅ |
| C-04 | Active 55/45 seasonal naive / 3MA blend forecast achieves ~6.49% MAPE on synthetic seasonal data | `results/forecast.json` | `active_method_mape_pct` | `6.49` | VERIFIED ✅ |
| C-05 | RAG RRF with lexical reranker achieves 95.0% Recall@3 | `results/rag.json` | `metrics.rrf+rerank.recall@3` | `0.95` | VERIFIED ✅ |
| C-06 | Intent parser extracts product SKUs with 100% accuracy | `results/intent.json` | `metrics.field_accuracies.product` | `1.0` | VERIFIED ✅ |
| C-07 | Intent parser extracts requested quantities with 100% accuracy | `results/intent.json` | `metrics.field_accuracies.quantity` | `1.0` | VERIFIED ✅ |
| C-08 | Intent parser extracts horizons with 100% accuracy | `results/intent.json` | `metrics.field_accuracies.horizon` | `1.0` | VERIFIED ✅ |
| C-09 | Overall exact match on 100 intent benchmark queries | `results/intent.json` | `metrics.overall_exact_match` | `0.86` | VERIFIED ✅ |
| C-10 | Supervisor guard prevents agent omission (100% complete specialist sets) | `results/ablation.json` | `metrics.supervisor_guard.guarded_valid_rate` | `1.0` | VERIFIED ✅ |
| C-11 | Explanation faithfulness guard catches 100% of injected numerical hallucinations | `results/ablation.json` | `metrics.faithfulness_guard.hallucination_catch_rate` | `1.0` | VERIFIED ✅ |
| C-12 | Replan whitelist recovery rate on solvable constrained scenarios | `results/ablation.json` | `metrics.replan_recovery.replan_recovery_rate` | `1.0` | VERIFIED ✅ |
