# Audit of Documentation Discrepancies vs. Ground Truth Code (T0.3)

**Date:** 2026-10-05  
**Methodology:** Direct inspection of active code files (`backend/app/`, `backend/tests/`) in accordance with Rule **R1** and Task **T0.3**.

---

## Discrepancy Resolution Matrix

| Item | Earlier Reports / Claims | Architecture Doc / Recent Reports | Actual Code Implementation (Ground Truth) | Verified File & Line | Resolution / Action for Docs |
|---|---|---|---|---|---|
| **Embedding Dimension** | 384 dimensions | `Vector(768)` | `settings.embedding_dim = 768`; `Vector(settings.embedding_dim)` | [backend/app/core/config.py:L21](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/core/config.py#L21), [backend/app/db/models.py:L226](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/db/models.py#L226) | **Code wins.** Update all docs to state 768 dimensions (Gemini `text-embedding-004` compatible). |
| **RRF Weights & Fusion** | Weights 0.6 dense / 0.4 sparse | Equal weights + lexical rerank | Equal Reciprocal Rank Fusion ($k=60$) for dense & sparse ranks, followed by $0.15 \times \text{lexical\_overlap}$ reranking. | [backend/app/rag/search.py:L54-L66](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/rag/search.py#L54-L66) | **Code wins.** Standardize docs to describe equal RRF ($k=60$) + lexical overlap reranking. |
| **Sparse Query Syntax** | `websearch_to_tsquery`, `ts_rank_cd` | `plainto_tsquery`, `ts_rank` | SQL executes `plainto_tsquery('english', :q)` and `ts_rank(c.tsv, plainto_tsquery('english', :q))` | [backend/app/rag/search.py:L41-L47](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/rag/search.py#L41-L47) | **Code wins.** Correct all doc references to `plainto_tsquery` and `ts_rank`. |
| **Forecast Blend Weights** | 60% seasonal / 40% moving avg | 55% seasonal / 45% moving avg | `0.55 * seasonal + 0.45 * recent` | [backend/app/agents/demand.py:L20](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/agents/demand.py#L20) | **Code wins.** Document 55/45 blend; CV parameter search scheduled in T1.3. |
| **Low-Risk Sourcing Rules** | Reliability $\ge 0.90$; High-risk $\le 15\%$ | Reliability $\ge 0.70$; High-risk excluded | `weighted_rel >= 0.90 * total`; `high_vars <= 0.15 * total`; `single_supplier <= 0.60 * total` | [backend/app/optimization/solver.py:L145-L163](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/optimization/solver.py#L145-L163) | **Code wins.** Standardize docs to state $\ge 0.90$ weighted reliability, $\le 15\%$ high-risk share, and $\le 60\%$ single-vendor cap. |
| **MILP Variables & MOQ** | `x` only; MOQ as implication | `x` + binary $y_s$ | Decision variables $x_{s,r} \in \mathbb{Z}_{\ge 0}$ with binary indicators $y_s \in \{0,1\}$: $\sum x \le \text{cap}_s \cdot y_s$ and $\sum x \ge \text{moq}_s \cdot y_s$. | [backend/app/optimization/solver.py:L117-L127](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/optimization/solver.py#L117-L127) | **Code wins.** Include explicit binary $y_s$ formulation in all documentation. |
| **Warehouse Inbound Capacity** | Present | Absent in summary table | Implemented: $\sum_{(s,r) \to w} x_{s,r} \le \max(0, \text{capacity}_w - \text{on\_hand}_w)$ | [backend/app/optimization/solver.py:L130-L142](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/optimization/solver.py#L130-L142) | **Code wins.** Document warehouse inbound remaining capacity constraint. |
| **Test Suite Count** | 19 / 20 tests | 23 tests | Exactly 23 collected test functions across 3 files (8 pipeline, 4 api, 11 extended verification). | [backend/tests/](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/tests) | **Code wins.** Fix test count to 23 (and expand with invariant tests in Phase 1). |
| **Validation vs. Solve Order** | Validate before Solve (diagram error) | Solve $\to$ Validate | StateGraph edge order: `specialists` $\to$ `solve` $\to$ `validate` $\to$ `should_replan` (`replan` or `explain`) | [backend/app/graph/graph.py:L37-L45](file:///e:/Agentic_AI-main/Agentic_AI-main/backend/app/graph/graph.py#L37-L45) | **Code wins.** Fix any legacy diagrams to show `solve` $\to$ `validate`. |

---

## Conclusion

All 9 cross-document contradiction items have been audited against the physical codebase and resolved unambiguously.
No items remain in an "unknown" state. Documentation updates during Phase 5 will strictly reflect these ground truth resolutions.
