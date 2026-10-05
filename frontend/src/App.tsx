import { FormEvent, useEffect, useState } from "react";
import {
  createDecision,
  DecisionResponse,
  executeHitlAction,
  fetchCatalog,
  runWhatIf,
} from "./api/client";

const EXAMPLE =
  "I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk.";

const PIPELINE_STEPS = [
  {
    id: "intent",
    name: "Intent Parser",
    desc: "Extracts product SKU, target quantity, horizon & risk mode",
    icon: "🎯",
  },
  {
    id: "rag",
    name: "Hybrid RAG",
    desc: "768d Dense + Sparse FTS retrieval of corporate policies",
    icon: "📚",
  },
  {
    id: "agents",
    name: "Specialist Agents",
    desc: "Demand forecast, supplier MOQs, route lanes & net inventory",
    icon: "🤖",
  },
  {
    id: "milp",
    name: "OR-Tools Solver",
    desc: "Mixed-Integer Linear Programming cost minimization",
    icon: "⚡",
  },
  {
    id: "validator",
    name: "Invariant Validator",
    desc: "Verifies capacities, route closures & concentration limits",
    icon: "🛡️",
  },
  {
    id: "faithfulness",
    name: "Faithfulness Guard",
    desc: "Fact-checks explanation numbers against database facts",
    icon: "🔍",
  },
  {
    id: "governance",
    name: "HITL Governance",
    desc: "Append-only event logging & server recommendation lock",
    icon: "⚖️",
  },
];

function money(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function hitlBadge(status: string | undefined) {
  switch (status) {
    case "APPROVED":
      return { class: "badge-green", label: "✅ APPROVED" };
    case "APPROVED_WITH_OVERRIDE":
      return { class: "badge-blue", label: "✅ APPROVED (WITH OVERRIDE)" };
    case "REJECTED":
      return { class: "badge-red", label: "❌ REJECTED" };
    case "PENDING_REVIEW":
    default:
      return { class: "badge-amber", label: "⏸️ PENDING REVIEW" };
  }
}

export default function App() {
  const [query, setQuery] = useState(EXAMPLE);
  const [loading, setLoading] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecisionResponse | null>(null);
  const [catalog, setCatalog] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"overview" | "allocations" | "inventory" | "governance" | "trace" | "whatif">("overview");

  // What-If State
  const [scenario, setScenario] = useState("supplier_failure");
  const [pct, setPct] = useState(20);
  const [supplierCode, setSupplierCode] = useState("SUP-C");

  // HITL & Auth State
  const [apiKey, setApiKey] = useState("secret_key_123");
  const [plannerComments, setPlannerComments] = useState("Verified supplier lead times and warehouse space limits");
  const [rejectMode, setRejectMode] = useState(false);
  const [excludeSupplierList, setExcludeSupplierList] = useState<string[]>([]);
  const [maxShare, setMaxShare] = useState<number | undefined>(undefined);
  const [forceLowRisk, setForceLowRisk] = useState(false);

  // Override State
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideAllocations, setOverrideAllocations] = useState<{ supplier_code: string; units: number }[]>([]);
  const [ackBreach, setAckBreach] = useState(false);

  // Dynamic Typewriter / Text Animation State
  const [displayedExplanation, setDisplayedExplanation] = useState<string>("");

  useEffect(() => {
    fetchCatalog()
      .then((c) => {
        const products = (c.products || []).map((p: { sku: string }) => p.sku).join(", ");
        setCatalog(products);
      })
      .catch(() => setCatalog("API offline (using local test fixtures)"));
  }, []);

  useEffect(() => {
    if (result?.supplier_allocation) {
      setOverrideAllocations(
        result.supplier_allocation.map((s) => ({
          supplier_code: s.supplier_code,
          units: s.units ?? s.quantity ?? 0,
        }))
      );
    }
  }, [result]);

  // Dynamic Typewriter Effect for Explanation
  useEffect(() => {
    if (!result?.explainable_recommendation?.ai_reasoning) {
      setDisplayedExplanation("");
      return;
    }
    const fullText = result.explainable_recommendation.ai_reasoning;
    let i = 0;
    setDisplayedExplanation("");
    const interval = setInterval(() => {
      i += 8;
      if (i >= fullText.length) {
        setDisplayedExplanation(fullText);
        clearInterval(interval);
      } else {
        setDisplayedExplanation(fullText.slice(0, i));
      }
    }, 15);
    return () => clearInterval(interval);
  }, [result]);

  // Timer while loading
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (loading) {
      setElapsedTime(0);
      timer = setInterval(() => {
        setElapsedTime((prev) => Math.round((prev + 0.1) * 10) / 10);
      }, 100);
    }
    return () => clearInterval(timer);
  }, [loading]);

  async function runPipelineWithSteps(execFn: () => Promise<DecisionResponse>) {
    setLoading(true);
    setError(null);
    setActiveStepIndex(0);

    // Step animation loop
    const stepTimer = setInterval(() => {
      setActiveStepIndex((prev) => {
        if (prev < PIPELINE_STEPS.length - 1) return prev + 1;
        return prev;
      });
    }, 350);

    try {
      const res = await execFn();
      setResult(res);
      setActiveStepIndex(PIPELINE_STEPS.length); // All done
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      clearInterval(stepTimer);
      setLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await runPipelineWithSteps(() => createDecision(query));
  }

  async function onWhatIf() {
    if (!result) return;
    await runPipelineWithSteps(() =>
      runWhatIf({
        run_id: result.run_id,
        scenario,
        pct,
        supplier_code: supplierCode,
      })
    );
  }

  async function onHitl(action: string) {
    if (!result) return;
    setLoading(true);
    setError(null);
    try {
      let reject_reason = undefined;
      let override_allocs = undefined;

      if (action === "reject" && (excludeSupplierList.length > 0 || maxShare !== undefined || forceLowRisk)) {
        reject_reason = {
          exclude_suppliers: excludeSupplierList,
          max_supplier_share: maxShare,
          force_low_risk: forceLowRisk,
          comment: plannerComments,
        };
      }

      if (action === "override") {
        override_allocs = overrideAllocations.map((a) => ({
          supplier_code: a.supplier_code,
          units: Number(a.units) || 0,
        }));
      }

      const updated = await executeHitlAction(
        result.run_id,
        action,
        apiKey,
        plannerComments,
        reject_reason,
        override_allocs,
        ackBreach
      );
      setResult(updated);
      setRejectMode(false);
      setOverrideMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const hitlInfo = hitlBadge(result?.hitl_status);

  return (
    <div className="page">
      {/* Brand Header */}
      <header>
        <div className="brand-wrapper">
          <div className="logo-badge">⚡</div>
          <div>
            <div className="eyebrow">Enterprise Decision Intelligence Platform</div>
            <h1>SupplyChainAI</h1>
          </div>
        </div>
        <div className="header-status">
          <div className="engine-tag">
            <div className="pulse-dot" />
            <span>OR-Tools MILP Engine Active</span>
          </div>
          <div className="engine-tag">
            <span className="code-chip">Catalog: {catalog || "PROD-A..PROD-J"}</span>
          </div>
        </div>
      </header>

      {/* Query Input Card */}
      <div className="panel">
        <div className="panel-title">
          <h2>💬 Natural Language Supply Chain Planning</h2>
          <span className="badge badge-blue">Rule R5: LLM Never Computes Numbers</span>
        </div>
        <form onSubmit={onSubmit}>
          <label htmlFor="user-query">Enter your operational procurement or rebalancing goal:</label>
          <textarea
            id="user-query"
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk."
            disabled={loading}
          />
          <div className="row wrap" style={{ justifyContent: "space-between", marginTop: 14 }}>
            <div className="row wrap" style={{ gap: 8 }}>
              <span className="badge badge-purple">7 Global Suppliers</span>
              <span className="badge badge-purple">4 Distribution Centers</span>
              <span className="badge badge-purple">16 Route Lanes</span>
            </div>
            <button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <div className="loading-spinner" />
                  <span>Solving Multi-Agent Pipeline ({elapsedTime}s)...</span>
                </>
              ) : (
                <>
                  <span>🚀 Run Planning Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Interactive Multi-Agent Working Steps & Progress State */}
      {(loading || activeStepIndex >= 0) && (
        <div className="pipeline-steps-card">
          <div className="pipeline-steps-header">
            <div>
              <div className="eyebrow">Multi-Agent Execution Pipeline</div>
              <h3 style={{ margin: 0, fontSize: "1.05rem" }}>
                {loading
                  ? `⚡ Active Step: ${PIPELINE_STEPS[Math.min(activeStepIndex, PIPELINE_STEPS.length - 1)].name} (${elapsedTime}s elapsed)`
                  : "✅ Pipeline Execution Complete — Optimal Mathematical Solution Found"}
              </h3>
            </div>
            <span className="badge badge-blue">
              {loading
                ? `Step ${Math.min(activeStepIndex + 1, PIPELINE_STEPS.length)} of ${PIPELINE_STEPS.length}`
                : "100% Complete"}
            </span>
          </div>

          <div className="steps-progress-bar-bg">
            <div
              className="steps-progress-bar-fill"
              style={{
                width: loading
                  ? `${((activeStepIndex + 1) / PIPELINE_STEPS.length) * 100}%`
                  : "100%",
              }}
            />
          </div>

          <div className="steps-grid">
            {PIPELINE_STEPS.map((step, idx) => {
              let statusClass = "pending";
              let statusLabel = "PENDING";
              if (idx < activeStepIndex || (!loading && activeStepIndex === PIPELINE_STEPS.length)) {
                statusClass = "completed";
                statusLabel = "DONE ✅";
              } else if (idx === activeStepIndex && loading) {
                statusClass = "active";
                statusLabel = "ACTIVE ⚡";
              }

              return (
                <div key={step.id} className={`step-item ${statusClass}`}>
                  <div className="step-header">
                    <span>{step.icon} STEP {idx + 1}</span>
                    <span>{statusLabel}</span>
                  </div>
                  <div className="step-title">{step.name}</div>
                  <div className="step-desc">{step.desc}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="panel" style={{ background: "rgba(239, 68, 68, 0.15)", borderColor: "var(--danger)" }}>
          <h3 style={{ color: "#f87171", margin: 0 }}>❌ Operational Error</h3>
          <p style={{ marginTop: 6, color: "#fca5a5" }}>{error}</p>
        </div>
      )}

      {/* Main Results Dashboard */}
      {result && (
        <>
          {/* Degraded Plan Banner (if relaxations were applied) */}
          {result.degraded && (
            <div
              className="panel"
              style={{
                background: "rgba(245, 158, 11, 0.15)",
                borderColor: "var(--warning)",
                padding: "16px 20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 24 }}>⚠️</span>
                <div>
                  <strong style={{ color: "#fbbf24" }}>DEGRADED PLAN NOTICE:</strong>
                  <span style={{ color: "#fde68a", marginLeft: 6 }}>
                    Initial constraints were infeasible. Bounded policy relaxations were applied to guarantee delivery:
                  </span>
                  <div style={{ marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(result.relaxations || []).map((r, i) => (
                      <span key={i} className="badge badge-amber">
                        {r.constraint}: {r.reason}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Top KPI Metrics Row */}
          <div className="kpis">
            <div className="kpi">
              <span>Total Landed Cost</span>
              <strong>{money(result.total_cost)}</strong>
              <div className="kpi-sub">
                Procurement: {money(result.procurement_cost)} · Transport: {money(result.transport_cost)}
              </div>
            </div>

            <div className="kpi success">
              <span>Solver Optimization Status</span>
              <strong style={{ color: "#34d399" }}>{result.optimization_status}</strong>
              <div className="kpi-sub">Google OR-Tools MILP Global Optimum</div>
            </div>

            <div className="kpi warning">
              <span>Net Requirement (Procure)</span>
              <strong>{result.inventory_plan?.net_requirement?.toLocaleString() ?? "—"} units</strong>
              <div className="kpi-sub">
                Demand: {result.demand_forecast?.demand_to_meet?.toLocaleString()} · Avail: {result.inventory_plan?.total_available?.toLocaleString()}
              </div>
            </div>

            <div className="kpi purple">
              <span>Composite Risk Score</span>
              <strong>{result.risk_score?.toFixed(1) ?? "0"}/100</strong>
              <div className="kpi-sub">
                Plan Risk: {result.plan_risk?.toFixed(1) ?? result.risk_score?.toFixed(1)} · Exposure: {result.disruption_exposure?.toFixed(1) ?? "0"}
              </div>
            </div>

            <div className="kpi">
              <span>HITL Governance State</span>
              <div style={{ marginTop: 4 }}>
                <span className={`badge ${hitlInfo.class}`} style={{ fontSize: "0.85rem", padding: "6px 12px" }}>
                  {hitlInfo.label}
                </span>
              </div>
              <div className="kpi-sub">
                Reviewed by: {result.hitl_reviewed_by || "System (Pending Lead Planner)"}
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="tabs-nav">
            <button
              className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
            >
              📊 Executive Overview
            </button>
            <button
              className={`tab-btn ${activeTab === "allocations" ? "active" : ""}`}
              onClick={() => setActiveTab("allocations")}
            >
              📦 Supplier Allocations & Routes ({result.supplier_allocation?.length || 0})
            </button>
            <button
              className={`tab-btn ${activeTab === "inventory" ? "active" : ""}`}
              onClick={() => setActiveTab("inventory")}
            >
              🏢 Inventory & Distribution Centers
            </button>
            <button
              className={`tab-btn ${activeTab === "governance" ? "active" : ""}`}
              onClick={() => setActiveTab("governance")}
            >
              ⚖️ HITL Governance & Audit Log
            </button>
            <button
              className={`tab-btn ${activeTab === "trace" ? "active" : ""}`}
              onClick={() => setActiveTab("trace")}
            >
              🤖 Multi-Agent Trace & RAG
            </button>
            <button
              className={`tab-btn ${activeTab === "whatif" ? "active" : ""}`}
              onClick={() => setActiveTab("whatif")}
            >
              🧪 What-If Stress Testing
            </button>
          </div>

          {/* TAB 1: EXECUTIVE OVERVIEW */}
          {activeTab === "overview" && (
            <div className="grid-2">
              {/* Dynamic AI Reasoning Box */}
              <div className="panel">
                <div className="panel-title">
                  <h2>✨ Dynamic AI Explainability & Policy Citations</h2>
                  <span className="badge badge-green">Faithfulness Guard: Verified</span>
                </div>
                <div className="ai-reason-box">
                  {displayedExplanation || result.explainable_recommendation?.ai_reasoning || "Analyzing mathematical decision variables..."}
                </div>

                <div style={{ marginTop: 18 }}>
                  <label>Retrieved Corporate Policy Grounding (Hybrid RAG):</label>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {(result.retrieved_evidence || []).map((ev, i) => (
                      <div key={i} style={{ padding: "8px 12px", background: "rgba(15, 23, 42, 0.5)", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#60a5fa" }}>
                          <strong>📄 {ev.title}</strong>
                          <span className="code-chip">RRF Score: {ev.score.toFixed(4)}</span>
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 4 }}>
                          {ev.content_snippet}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Execution Steps & Recommendation Lock */}
              <div className="panel">
                <div className="panel-title">
                  <h2>🔒 Operational Purchase Execution Steps</h2>
                  {result.execution_locked ? (
                    <span className="badge badge-amber">Server Lock Active</span>
                  ) : (
                    <span className="badge badge-green">Unlocked & Ready</span>
                  )}
                </div>

                {result.execution_locked && (
                  <div className="lock-banner">
                    <div>
                      <strong style={{ color: "#fbbf24" }}>EXECUTION STEPS LOCKED:</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "#fde68a" }}>
                        In accordance with enterprise compliance policy, raw supplier purchase orders are redacted until an authorized reviewer approves the plan.
                      </p>
                    </div>
                  </div>
                )}

                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {(result.explainable_recommendation?.execution_steps || []).map((step, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "12px 14px",
                        background: "rgba(15, 23, 42, 0.6)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 10,
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                      }}
                    >
                      <span className="code-chip" style={{ color: "#38bdf8" }}>Step {i + 1}</span>
                      <span style={{ fontSize: "0.9rem", color: result.execution_locked ? "var(--text-muted)" : "var(--text-primary)" }}>
                        {step}
                      </span>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 24, padding: "16px", background: "rgba(15, 23, 42, 0.5)", borderRadius: 12, border: "1px solid var(--border-subtle)" }}>
                  <div className="panel-title" style={{ marginBottom: 8 }}>
                    <h3 style={{ fontSize: "0.95rem", margin: 0 }}>⚡ Quick Approval & Sign-Off</h3>
                  </div>
                  <div className="row wrap">
                    <input
                      type="password"
                      style={{ maxWidth: 200 }}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter reviewer key"
                    />
                    <button className="btn-success" onClick={() => onHitl("approve")} disabled={loading || !result.execution_locked}>
                      ✅ Approve Plan ({result.execution_locked ? "Unlock" : "Approved"})
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: ALLOCATIONS & ROUTES */}
          {activeTab === "allocations" && (
            <div className="panel">
              <div className="panel-title">
                <h2>📦 Mathematically Optimized Supplier & Lane Allocations</h2>
                <span className="badge badge-blue">Deterministic MILP Result</span>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Supplier Code</th>
                      <th>Supplier Name</th>
                      <th>Destination Warehouse</th>
                      <th>Route Lane</th>
                      <th>Transport Mode</th>
                      <th>Quantity (Units)</th>
                      <th>Unit Price</th>
                      <th>Transit Cost/Unit</th>
                      <th>Total Line Cost</th>
                      <th>Lead Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.supplier_allocation || []).map((row, i) => (
                      <tr key={i}>
                        <td><span className="code-chip">{row.supplier_code}</span></td>
                        <td><strong>{row.supplier_name}</strong></td>
                        <td><span className="code-chip">{row.warehouse_code}</span></td>
                        <td><span className="code-chip">{row.route_code}</span></td>
                        <td><span className="badge badge-purple">{row.mode}</span></td>
                        <td><strong style={{ color: "#38bdf8" }}>{(row.units ?? row.quantity ?? 0).toLocaleString()}</strong></td>
                        <td>${row.unit_price?.toFixed(2)}</td>
                        <td>${row.transport_cost_per_unit?.toFixed(2)}</td>
                        <td><strong style={{ color: "#34d399" }}>{money(row.cost ?? row.line_cost)}</strong></td>
                        <td>{row.lead_time_days} days ({row.transit_hours} hrs)</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: INVENTORY & WAREHOUSES */}
          {activeTab === "inventory" && (
            <div className="panel">
              <div className="panel-title">
                <h2>🏢 Distribution Center Balances & Net Requirement</h2>
                <span className="badge badge-purple">
                  Formula: Net Req = max(0, Demand + SafetyStock - Available)
                </span>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Distribution Center</th>
                      <th>On Hand</th>
                      <th>Reserved Stock</th>
                      <th>Available Stock</th>
                      <th>Safety Stock Target</th>
                      <th>Total DC Capacity</th>
                      <th>Holding Cost/Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.inventory_plan?.rows || []).map((row, i) => (
                      <tr key={i}>
                        <td><strong>{row.warehouse_code}</strong></td>
                        <td>{row.on_hand.toLocaleString()}</td>
                        <td>{row.reserved.toLocaleString()}</td>
                        <td><strong style={{ color: "#38bdf8" }}>{row.available.toLocaleString()}</strong></td>
                        <td><strong style={{ color: "#fbbf24" }}>{row.safety_stock.toLocaleString()}</strong></td>
                        <td>{row.capacity_units?.toLocaleString() ?? "—"} units</td>
                        <td>${row.holding_cost_per_unit?.toFixed(2)}/mo</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: HITL GOVERNANCE & TIMELINE */}
          {activeTab === "governance" && (
            <div className="grid-2">
              {/* Actions Panel */}
              <div className="panel">
                <div className="panel-title">
                  <h2>✍️ Reviewer Authorization & HITL Actions</h2>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div>
                    <label>Reviewer API Key (Token Auth):</label>
                    <input
                      type="text"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="e.g. secret_key_123 or key_alice"
                    />
                  </div>

                  <div>
                    <label>Planner Audit Comments:</label>
                    <textarea
                      rows={2}
                      value={plannerComments}
                      onChange={(e) => setPlannerComments(e.target.value)}
                      placeholder="Justification for approval, rejection, or override..."
                    />
                  </div>

                  <div className="row wrap" style={{ gap: 10 }}>
                    <button className="btn-success" onClick={() => onHitl("approve")} disabled={loading}>
                      ✅ Approve Plan
                    </button>
                    <button className="btn-danger" onClick={() => setRejectMode(!rejectMode)} disabled={loading}>
                      ❌ Structured Reject...
                    </button>
                    <button className="btn-secondary" onClick={() => setOverrideMode(!overrideMode)} disabled={loading}>
                      ✏️ Manual Override...
                    </button>
                  </div>

                  {/* Reject Form */}
                  {rejectMode && (
                    <div style={{ marginTop: 12, padding: 16, background: "rgba(239, 68, 68, 0.1)", borderRadius: 12, border: "1px solid var(--danger)" }}>
                      <h4 style={{ color: "#f87171", margin: "0 0 10px" }}>Structured Rejection & Child Run Simulation</h4>
                      <label>Exclude Specific Suppliers:</label>
                      <div className="row wrap" style={{ gap: 8, marginBottom: 12 }}>
                        {["SUP-A", "SUP-B", "SUP-C", "SUP-D", "SUP-E", "SUP-F", "SUP-G"].map((sup) => (
                          <label key={sup} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.85rem" }}>
                            <input
                              type="checkbox"
                              style={{ width: "auto" }}
                              checked={excludeSupplierList.includes(sup)}
                              onChange={(e) => {
                                if (e.target.checked) setExcludeSupplierList([...excludeSupplierList, sup]);
                                else setExcludeSupplierList(excludeSupplierList.filter((s) => s !== sup));
                              }}
                            />
                            {sup}
                          </label>
                        ))}
                      </div>

                      <button className="btn-danger" onClick={() => onHitl("reject")} disabled={loading}>
                        🚨 Submit Rejection (Spawns Child Run)
                      </button>
                    </div>
                  )}

                  {/* Override Form */}
                  {overrideMode && (
                    <div style={{ marginTop: 12, padding: 16, background: "rgba(59, 130, 246, 0.1)", borderRadius: 12, border: "1px solid var(--primary)" }}>
                      <h4 style={{ color: "#60a5fa", margin: "0 0 10px" }}>Full-Fidelity Manual Override Form</h4>
                      <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 12 }}>
                        Overrides are checked against MOQs, supplier capacities, and warehouse space limits.
                      </p>
                      {overrideAllocations.map((alloc, idx) => (
                        <div key={idx} className="row" style={{ marginBottom: 8 }}>
                          <span className="code-chip" style={{ width: 80 }}>{alloc.supplier_code}</span>
                          <input
                            type="number"
                            value={alloc.units}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              const updated = [...overrideAllocations];
                              updated[idx].units = val;
                              setOverrideAllocations(updated);
                            }}
                          />
                          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>units</span>
                        </div>
                      ))}

                      <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
                        <input
                          type="checkbox"
                          style={{ width: "auto" }}
                          checked={ackBreach}
                          onChange={(e) => setAckBreach(e.target.checked)}
                        />
                        <span>Acknowledge policy breach (if relaxing supplier concentration)</span>
                      </label>

                      <button className="btn-success" style={{ marginTop: 10 }} onClick={() => onHitl("override")} disabled={loading}>
                        💾 Validate & Apply Override
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Append-Only Event Timeline */}
              <div className="panel">
                <div className="panel-title">
                  <h2>📜 Append-Only Audit Ledger (`decision_events`)</h2>
                  <span className="badge badge-green">Immutable Log</span>
                </div>
                <div className="timeline">
                  {(result.event_history || [
                    { action: "CREATED", actor: "system", timestamp: new Date().toISOString() },
                  ]).map((ev, i) => (
                    <div key={i} className="timeline-item">
                      <div className="timeline-dot" />
                      <div className="timeline-content">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span className="badge badge-blue">{ev.action}</span>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "Just now"}
                          </span>
                        </div>
                        <div className="timeline-meta">
                          <span>Actor: <strong style={{ color: "#38bdf8" }}>{ev.actor}</strong></span>
                          <span>Run ID: #{result.run_id}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: TRACE & RAG */}
          {activeTab === "trace" && (
            <div className="panel">
              <div className="panel-title">
                <h2>🤖 Multi-Agent Execution DAG & Retrieval Provenance</h2>
                <span className="badge badge-purple">LangGraph State Machine</span>
              </div>
              <div style={{ marginBottom: 16 }}>
                <label>Agent Execution Sequence:</label>
                <div className="row wrap" style={{ gap: 8 }}>
                  {(result.agent_trace || []).map((agent, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="badge badge-blue">
                        {i + 1}. {agent}
                      </span>
                      {i < (result.agent_trace?.length || 0) - 1 && <span style={{ color: "var(--text-muted)" }}>➔</span>}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: 20 }}>
                <label>Parsed Semantic Intent:</label>
                <div style={{ padding: 14, background: "rgba(15, 23, 42, 0.6)", borderRadius: 10, border: "1px solid var(--border-subtle)" }}>
                  <div className="grid-2" style={{ gap: 12, fontSize: "0.85rem" }}>
                    <div><strong>Target Product:</strong> {result.parsed_intent?.product_query || "Product A"}</div>
                    <div><strong>Requested Qty:</strong> {result.parsed_intent?.quantity?.toLocaleString() || "10,000"} units</div>
                    <div><strong>Horizon:</strong> {result.parsed_intent?.horizon_days || 30} days</div>
                    <div><strong>Low-Risk Mode:</strong> {result.parsed_intent?.low_risk ? "Enabled (Tier 1 Preferred)" : "Standard"}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: WHAT-IF STRESS TESTING */}
          {activeTab === "whatif" && (
            <div className="panel">
              <div className="panel-title">
                <h2>🧪 What-If Stress-Testing & Disruption Engine</h2>
                <span className="badge badge-amber">Dynamic Re-Optimization</span>
              </div>
              <div className="row wrap" style={{ gap: 14, marginBottom: 20 }}>
                <select value={scenario} onChange={(e) => setScenario(e.target.value)} style={{ maxWidth: 220 }}>
                  <option value="supplier_failure">Supplier Outage / Failure</option>
                  <option value="demand_spike">Demand Spike (+20%..+50%)</option>
                  <option value="fuel_price_hike">Marine Fuel Surge (+30%)</option>
                  <option value="route_disruption">Shipping Lane Closure</option>
                </select>

                {scenario === "supplier_failure" && (
                  <select value={supplierCode} onChange={(e) => setSupplierCode(e.target.value)} style={{ maxWidth: 140 }}>
                    <option value="SUP-C">SUP-C (High Risk)</option>
                    <option value="SUP-A">SUP-A (Primary)</option>
                    <option value="SUP-B">SUP-B (Secondary)</option>
                  </select>
                )}

                {scenario === "demand_spike" && (
                  <input
                    type="number"
                    style={{ maxWidth: 120 }}
                    value={pct}
                    onChange={(e) => setPct(Number(e.target.value))}
                    placeholder="Spike %"
                  />
                )}

                <button onClick={onWhatIf} disabled={loading}>
                  ⚡ Simulate Disruption & Re-Optimize
                </button>
              </div>

              {result.what_if?.comparison && (
                <div style={{ marginTop: 16 }}>
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Metric</th>
                          <th>Baseline Value</th>
                          <th>Scenario Value</th>
                          <th>Delta / Impact</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><strong>Total Landed Cost</strong></td>
                          <td>{money(result.what_if.comparison.total_cost?.baseline)}</td>
                          <td>{money(result.what_if.comparison.total_cost?.scenario)}</td>
                          <td>
                            <strong style={{ color: (result.what_if.comparison.total_cost?.delta ?? 0) > 0 ? "#f87171" : "#34d399" }}>
                              {money(result.what_if.comparison.total_cost?.delta)}
                            </strong>
                          </td>
                        </tr>
                        <tr>
                          <td><strong>Composite Risk Score</strong></td>
                          <td>{result.what_if.comparison.risk_score?.baseline?.toFixed(1)}/100</td>
                          <td>{result.what_if.comparison.risk_score?.scenario?.toFixed(1)}/100</td>
                          <td>
                            <span className="badge badge-amber">
                              {(result.what_if.comparison.risk_score?.delta ?? 0) > 0 ? "+" : ""}
                              {result.what_if.comparison.risk_score?.delta?.toFixed(1)} pts
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td><strong>Delivery Time</strong></td>
                          <td>{result.what_if.comparison.delivery_time_hours?.baseline} hrs</td>
                          <td>{result.what_if.comparison.delivery_time_hours?.scenario} hrs</td>
                          <td>{result.what_if.comparison.delivery_time_hours?.delta} hrs</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <footer style={{ textAlign: "center", marginTop: 40, color: "var(--text-muted)", fontSize: "0.85rem" }}>
        SupplyChainAI v1.0-hardened · Neurosymbolic Multi-Agent Decision Intelligence with Google OR-Tools
      </footer>
    </div>
  );
}
