# SupplyChainAI Comprehensive Evaluation Report

*Generated on 2026-10-05T14:03:24.360234+00:00 from benchmark artifacts in `results/*.json`.*

---

## 1. Executive Summary

SupplyChainAI is a deterministic, optimization-bounded multi-agent decision system. 
Unlike demo prototypes that allow LLMs to calculate supply chain numbers, SupplyChainAI strictly enforces:
1. **Mathematical Invariance**: 100% of order allocations, supplier quantities, and costs are computed by OR-Tools MILP optimization.
2. **Zero Invariant Violations**: Guaranteed 0 hard constraint breaches across all tested scenarios.
3. **Auditability & Governance**: Append-only event logging, authenticated human reviewer gates, and structured override/rejection protocols.

---

## 2. Solver Evaluation & Invariants (T4.3)

Evaluated across 50 seeded scenarios encompassing demand spikes (0.2x–3.0x), supplier outages (0–2 failed vendors), and fuel cost surges (1.0x–2.0x).

| Metric | OR-Tools MILP Solver | Greedy Baseline |
|---|---|---|
| **Feasibility Rate** | 76.0% | 76.0% |
| **Hard Constraint Violations / Plan** | **0.0** (Target: 0) | 0.0 |
| **Cost Gap vs Greedy** | **-2.79% cheaper** | Baseline (0.0%) |
| **Infeasible Detection Accuracy** | **100.0%** | — |
| **Solve Time (p50)** | **7.02 ms** | < 1 ms |
| **Solve Time (p95)** | **14.06 ms** | < 1 ms |

---

## 3. RAG Retrieval Benchmark (T4.2)

Evaluated on `45` queries (including positive domain queries, SKU queries, paraphrases, and negative controls) over the 7 knowledge base markdown manuals.

| Retriever Configuration | MRR | MRR (95% CI) | Recall@3 | Recall@3 (95% CI) | nDCG@3 |
|---|---|---|---|---|---|
| **Sparse (BM25)** | 0.9333 | [0.875, 0.9875] | 0.9500 | [0.9, 0.9875] | 0.9130 |
| **Dense (768-dim)** | 0.3747 | [0.3084, 0.4515] | 0.4625 | [0.325, 0.6] | 0.3104 |
| **RRF Fusion** | 0.7000 | [0.5917, 0.7937] | 0.8750 | [0.7875, 0.95] | 0.7046 |
| **RRF + Lexical Rerank (Active)** | **0.8792** | [0.8083, 0.9458] | **0.9500** | [0.9, 0.9875] | **0.8728** |

---

## 4. Intent Extraction Benchmark (T4.4)

Evaluated on `100` labeled intent queries with colloquial, abbreviated, and adversarial user inputs.

| Evaluated Field | Exact Match Accuracy |
|---|---|
| **Product SKU (`product`)** | **100.0%** |
| **Requested Quantity (`quantity`)** | **100.0%** |
| **Planning Horizon (`horizon`)** | **100.0%** |
| **Low-Risk Preference (`low_risk`)** | **95.0%** |
| **Optimization Objective (`objective`)** | **90.0%** |
| **Overall Full-Query Exact Match** | **86.0%** |

---

## 5. Demand Forecasting Benchmark (T4.5)

Evaluated using rolling-origin cross-validation ($h=1, \text{min\_train}=12$) across historical monthly orders.

| Forecasting Method | MAPE (%) | Description |
|---|---|---|
| `naive_last` | 8.2% | Last observed month |
| `seasonal_naive_t12` | 5.68% | Same month previous year |
| `trailing_3ma` | 12.37% | 3-month moving average |
| `blend_w0.55` (Active) | **6.49%** | 55% Seasonal Naive + 45% 3MA Blend |

---

## 6. Agentic Ablations (T4.6)

| Agentic Feature | Measured Impact / Effect |
|---|---|
| **Supervisor Guard** | **100.0% valid agent sets** (vs 12.0% for unconstrained model) |
| **Replan Whitelist** | **100.0% recovery rate** on tightly-constrained infeasible scenarios |
| **Faithfulness Guard** | **100.0% hallucination catch rate** (0 numerical hallucinations reach user) |

---

## 7. Provenance and Replication

To reproduce all benchmarks from scratch:
```bash
make eval
```
Or run individual evaluation harnesses:
```bash
python scripts/eval_rag.py --seed 42
python scripts/eval_solver.py --seed 42
python scripts/eval_intent.py
python scripts/eval_forecast.py
python scripts/eval_ablation.py --seed 42
python scripts/build_report.py
```
