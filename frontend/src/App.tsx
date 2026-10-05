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

const LOADING_MESSAGES = [
  "🎯 Parsing natural language intent...",
  "📚 Retrieving corporate policies via Hybrid RAG (768d + FTS)...",
  "🤖 Running specialist agents (Demand, Supplier, Route, Inventory, Risk)...",
  "⚡ Executing Google OR-Tools MILP cost optimization...",
  "🛡️ Verifying mathematical constraints & invariants...",
  "🔍 Running faithfulness guard & formatting response...",
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
      return { bg: "#dcfce7", border: "#22c55e", color: "#14532d", label: "✅ APPROVED" };
    case "APPROVED_WITH_OVERRIDE":
      return { bg: "#dbeafe", border: "#3b82f6", color: "#1e3a5f", label: "✅ APPROVED (Override)" };
    case "REJECTED":
      return { bg: "#fee2e2", border: "#ef4444", color: "#7f1d1d", label: "❌ REJECTED" };
    case "PENDING_REVIEW":
    default:
      return { bg: "#fef9c3", border: "#eab308", color: "#713f12", label: "⏸️ PENDING REVIEW" };
  }
}

export default function App() {
  const [query, setQuery] = useState(EXAMPLE);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecisionResponse | null>(null);
  const [catalog, setCatalog] = useState<string>("");
  const [scenario, setScenario] = useState("supplier_failure");
  const [pct, setPct] = useState(20);
  const [supplierCode, setSupplierCode] = useState("SUP-C");

  // HITL & Auth State
  const [apiKey, setApiKey] = useState("secret_key_123");
  const [plannerComments, setPlannerComments] = useState("Verified supplier lead times and inventory safety stock");
  const [rejectMode, setRejectMode] = useState(false);
  const [excludeSupplierList, setExcludeSupplierList] = useState<string[]>([]);
  const [maxShare, setMaxShare] = useState<number | undefined>(undefined);
  const [forceLowRisk, setForceLowRisk] = useState(false);

  // Override State
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideAllocations, setOverrideAllocations] = useState<{ supplier_code: string; units: number }[]>([]);
  const [ackBreach, setAckBreach] = useState(false);

  useEffect(() => {
    fetchCatalog()
      .then((c) => {
        const products = (c.products || []).map((p: { sku: string }) => p.sku).join(", ");
        setCatalog(products);
      })
      .catch(() => setCatalog("PROD-A, PROD-B, PROD-C, PROD-D, PROD-E, PROD-F, PROD-G, PROD-H, PROD-I, PROD-J"));
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

  // Small dynamic loading message cycler
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      setLoadingStep(0);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev + 1) % LOADING_MESSAGES.length);
      }, 400);
    }
    return () => clearInterval(interval);
  }, [loading]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(await createDecision(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function onWhatIf() {
    if (!result) return;
    setLoading(true);
    setError(null);
    try {
      setResult(
        await runWhatIf({
          run_id: result.run_id,
          scenario,
          pct,
          supplier_code: supplierCode,
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
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

  const badge = hitlBadge(result?.validation?.hitl_status);
  const isPending = result?.validation?.hitl_status === "PENDING_REVIEW" || !result?.validation?.hitl_status;
  const isApproved =
    result?.validation?.hitl_status === "APPROVED" ||
    result?.validation?.hitl_status === "APPROVED_WITH_OVERRIDE";

  return (
    <div className="page">
      {/* ── Brand Header ── */}
      <header>
        <div>
          <p className="eyebrow">Enterprise Decision Intelligence Platform</p>
          <h1>SupplyChainAI</h1>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <span className="badge">SYNTHETIC DEMO DATA</span>
          <span className="hint" style={{ fontSize: "0.8rem" }}>
            Catalog: {catalog || "Loading..."}
          </span>
        </div>
      </header>

      {/* ── Natural Language Query Input ── */}
      <section className="panel">
        <h2>Supply Chain Planning Request</h2>
        <form onSubmit={onSubmit}>
          <label htmlFor="planner-query">Ask in plain English (Rule R5: OR-Tools solver computes all numbers):</label>
          <textarea
            id="planner-query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <div className="row wrap" style={{ justifyContent: "space-between", marginTop: 12 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setQuery(EXAMPLE)}
                style={{ fontSize: "0.85rem", padding: "8px 12px" }}
              >
                Insert Example Query
              </button>
              {loading && (
                <div className="loading-pill">
                  <div className="small-spinner" />
                  <span>{LOADING_MESSAGES[loadingStep]}</span>
                </div>
              )}
            </div>

            <button type="submit" disabled={loading}>
              {loading ? "Optimizing Plan..." : "⚡ Run Planning Pipeline"}
            </button>
          </div>
        </form>
      </section>

      {/* ── Error Banner ── */}
      {error && (
        <div className="error" style={{ marginBottom: "20px" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* ── Main Results View ── */}
      {result && (
        <>
          {/* ── Degraded Plan Notice ── */}
          {result.explainable_recommendation?.degraded && (
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #f59e0b",
                borderRadius: "12px",
                padding: "16px 20px",
                marginBottom: "20px",
                color: "#92400e",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 22 }}>⚠️</span>
                <div>
                  <strong>DEGRADED PLAN NOTICE:</strong> Initial hard constraints were infeasible. Bounded policy relaxations were applied:
                  <div style={{ marginTop: 4, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(result.explainable_recommendation?.relaxations_applied || []).map((r, i) => (
                      <span key={i} className="badge" style={{ background: "#fde68a", color: "#78350f" }}>
                        {r.constraint}: {r.before} ➔ {r.after}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── KPI Dashboard Cards ── */}
          <div className="kpis">
            <Kpi label="Total Optimized Cost" value={money(result.total_cost)} />
            <Kpi
              label="Solver Status"
              value={result.optimization_status || "—"}
              sub="Google OR-Tools MILP"
            />
            <Kpi
              label="Delivery Lead Time"
              value={result.delivery_time_hours != null ? `${result.delivery_time_hours} hrs` : "—"}
            />
            <Kpi
              label="Risk Score"
              value={
                result.validation?.plan_risk != null && result.validation?.disruption_exposure != null
                  ? `${result.validation.plan_risk.toFixed(1)}/100 (Exposure: ${result.validation.disruption_exposure.toFixed(1)})`
                  : result.risk_score != null
                  ? `${result.risk_score.toFixed(1)}/100`
                  : "—"
              }
            />
            <Kpi
              label="Forecast / Demand"
              value={
                result.demand_forecast
                  ? `${(result.demand_forecast.demand_to_meet ?? result.demand_forecast.forecast_units ?? 0).toLocaleString()} units`
                  : "—"
              }
              sub={result.demand_forecast?.method || "statistical"}
            />
            <Kpi
              label="Inventory Net Requirement"
              value={
                result.inventory_plan?.net_requirement != null
                  ? `${result.inventory_plan.net_requirement.toLocaleString()} units`
                  : "—"
              }
              sub={`Avail: ${result.inventory_plan?.total_available?.toLocaleString() ?? "—"}`}
            />
          </div>

          {/* ── What-If Stress Testing Panel ── */}
          <section className="panel">
            <h2>What-If Scenario Simulation</h2>
            <div className="row wrap">
              <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                <option value="supplier_failure">Supplier Outage / Failure</option>
                <option value="demand_spike">Demand Spike (+% percent)</option>
                <option value="fuel_price_hike">Fuel Price Hike (+% percent)</option>
                <option value="supplier_price_hike">Supplier Price Hike (+% percent)</option>
                <option value="inventory_loss">Inventory Loss (-% percent)</option>
                <option value="route_disruption">Route Lane Disruption</option>
              </select>

              {scenario === "supplier_failure" && (
                <select value={supplierCode} onChange={(e) => setSupplierCode(e.target.value)}>
                  <option value="SUP-C">SUP-C (High Risk, Primary)</option>
                  <option value="SUP-A">SUP-A (Primary)</option>
                  <option value="SUP-B">SUP-B (Secondary)</option>
                  <option value="SUP-D">SUP-D</option>
                  <option value="SUP-E">SUP-E</option>
                </select>
              )}

              {scenario.includes("spike") || scenario.includes("hike") || scenario.includes("loss") ? (
                <input
                  type="number"
                  style={{ width: "110px" }}
                  value={pct}
                  onChange={(e) => setPct(Number(e.target.value))}
                  placeholder="Percent %"
                />
              ) : null}

              <button type="button" onClick={onWhatIf} disabled={loading}>
                ⚡ Run What-If Scenario
              </button>
            </div>

            {result.what_if?.comparison && (
              <div style={{ marginTop: "16px" }}>
                <h3 style={{ fontSize: "0.95rem", marginBottom: "8px" }}>
                  Scenario Impact Comparison: {result.what_if.label || scenario}
                </h3>
                <table>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Baseline</th>
                      <th>Scenario</th>
                      <th>Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(result.what_if.comparison).map(([k, v]) => (
                      <tr key={k}>
                        <td>
                          <strong>{k.replace(/_/g, " ").toUpperCase()}</strong>
                        </td>
                        <td>{k.includes("cost") ? money(v.baseline) : v.baseline.toLocaleString()}</td>
                        <td>{k.includes("cost") ? money(v.scenario) : v.scenario.toLocaleString()}</td>
                        <td
                          style={{
                            color: v.delta > 0 && k.includes("cost") ? "#b91c1c" : v.delta < 0 ? "#15803d" : undefined,
                            fontWeight: 600,
                          }}
                        >
                          {v.delta > 0 ? "+" : ""}
                          {k.includes("cost") ? money(v.delta) : v.delta.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* ── Supplier Allocation & Routes Table ── */}
          <section className="panel">
            <h2>Mathematically Optimal Allocations &amp; Logistics Lanes</h2>
            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Destination DC</th>
                    <th>Route Code</th>
                    <th>Mode</th>
                    <th>Units</th>
                    <th>Unit Price</th>
                    <th>Transit / Unit</th>
                    <th>Line Cost</th>
                    <th>Lead Time</th>
                  </tr>
                </thead>
                <tbody>
                  {result.routes && result.routes.length > 0
                    ? result.routes.map((r, i) => (
                        <tr key={i}>
                          <td>
                            <strong>{r.supplier_code}</strong>
                          </td>
                          <td>{r.warehouse_code}</td>
                          <td>
                            <code>{r.route_code}</code>
                          </td>
                          <td>
                            <span className="badge" style={{ background: "#e0e7ff", color: "#3730a3" }}>
                              {r.mode}
                            </span>
                          </td>
                          <td>
                            <strong style={{ color: "#0284c7" }}>{r.quantity.toLocaleString()}</strong>
                          </td>
                          <td>${(r.line_cost / Math.max(r.quantity, 1)).toFixed(2)}</td>
                          <td>—</td>
                          <td>
                            <strong style={{ color: "#059669" }}>{money(r.line_cost)}</strong>
                          </td>
                          <td>
                            {r.lead_time_days} days ({r.transit_hours}h)
                          </td>
                        </tr>
                      ))
                    : result.supplier_allocation.map((s, i) => (
                        <tr key={i}>
                          <td>
                            <strong>{s.supplier_code}</strong> ({s.supplier_name})
                          </td>
                          <td>WH-SIN / Multi</td>
                          <td>Lane {i + 1}</td>
                          <td>Ocean/Rail</td>
                          <td>
                            <strong style={{ color: "#0284c7" }}>{(s.units ?? s.quantity ?? 0).toLocaleString()}</strong>
                          </td>
                          <td>${s.unit_price?.toFixed(2) ?? "—"}</td>
                          <td>—</td>
                          <td>
                            <strong style={{ color: "#059669" }}>{money(s.cost)}</strong>
                          </td>
                          <td>—</td>
                        </tr>
                      ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ── Inventory DC Breakdown Table ── */}
          {result.inventory_plan?.rows && (
            <section className="panel">
              <h2>Distribution Center Inventory &amp; Safety Stock</h2>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Distribution Center</th>
                      <th>On Hand</th>
                      <th>Reserved</th>
                      <th>Available</th>
                      <th>Safety Stock Target</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.inventory_plan.rows.map((r, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{r.warehouse_code}</strong>
                        </td>
                        <td>{r.on_hand.toLocaleString()}</td>
                        <td>{r.reserved.toLocaleString()}</td>
                        <td>
                          <strong style={{ color: "#0284c7" }}>{r.available.toLocaleString()}</strong>
                        </td>
                        <td>
                          <strong style={{ color: "#d97706" }}>{r.safety_stock.toLocaleString()}</strong>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── HITL Governance & Authorization Console ── */}
          <section className="panel" style={{ border: `2px solid ${badge.border}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
              <h2>Human-in-the-Loop (HITL) Governance Console</h2>
              <span
                style={{
                  background: badge.bg,
                  border: `1px solid ${badge.border}`,
                  color: badge.color,
                  padding: "6px 14px",
                  borderRadius: "999px",
                  fontWeight: 700,
                  fontSize: "0.85rem",
                }}
              >
                {badge.label}
              </span>
            </div>

            {isPending && (
              <>
                <p className="hint" style={{ marginTop: "8px" }}>
                  This recommendation is in <strong>PENDING_REVIEW</strong>. In accordance with enterprise governance, operational purchase orders are locked until signed off with an authenticated planner key.
                </p>

                <div className="row wrap" style={{ marginTop: "14px", gap: "12px" }}>
                  <div style={{ flex: "1 1 200px" }}>
                    <label style={{ fontSize: "0.8rem" }}>Reviewer API Key (Token):</label>
                    <input
                      type="text"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="e.g. secret_key_123 or key_alice"
                    />
                  </div>
                  <div style={{ flex: "2 1 300px" }}>
                    <label style={{ fontSize: "0.8rem" }}>Planner Audit Justification:</label>
                    <input
                      type="text"
                      value={plannerComments}
                      onChange={(e) => setPlannerComments(e.target.value)}
                      placeholder="e.g. Approved after reviewing lead times"
                    />
                  </div>
                </div>

                <div className="row wrap" style={{ marginTop: "14px", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => onHitl("approve")}
                    disabled={loading}
                    style={{ backgroundColor: "#15803d", color: "#fff" }}
                  >
                    ✅ Approve Recommendation
                  </button>
                  <button
                    type="button"
                    onClick={() => setRejectMode(!rejectMode)}
                    disabled={loading}
                    style={{ backgroundColor: "#b91c1c", color: "#fff" }}
                  >
                    ❌ Structured Reject...
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverrideMode(!overrideMode)}
                    disabled={loading}
                    className="btn-secondary"
                  >
                    ✏️ Manual Override...
                  </button>
                </div>

                {/* Structured Rejection Panel */}
                {rejectMode && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "14px",
                      backgroundColor: "#fef2f2",
                      border: "1px solid #f87171",
                      borderRadius: "8px",
                    }}
                  >
                    <h4 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>Structured Rejection &amp; Child Run</h4>
                    <p style={{ fontSize: "0.85rem", color: "#7f1d1d", margin: "0 0 10px 0" }}>
                      Select constraints to apply to the automatically spawned child re-optimization:
                    </p>
                    <div style={{ display: "flex", gap: "14px", flexWrap: "wrap" }}>
                      {["SUP-A", "SUP-B", "SUP-C", "SUP-D", "SUP-E"].map((code) => (
                        <label key={code} style={{ fontSize: "0.85rem", cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={excludeSupplierList.includes(code)}
                            onChange={(e) => {
                              if (e.target.checked) setExcludeSupplierList([...excludeSupplierList, code]);
                              else setExcludeSupplierList(excludeSupplierList.filter((s) => s !== code));
                            }}
                            style={{ marginRight: "4px" }}
                          />
                          Exclude {code}
                        </label>
                      ))}
                    </div>
                    <div style={{ marginTop: "8px" }}>
                      <label style={{ fontSize: "0.85rem" }}>
                        <input
                          type="checkbox"
                          checked={forceLowRisk}
                          onChange={(e) => setForceLowRisk(e.target.checked)}
                          style={{ marginRight: "4px" }}
                        />
                        Force Low-Risk Suppliers Only
                      </label>
                    </div>
                    <div style={{ marginTop: "10px" }}>
                      <button
                        type="button"
                        onClick={() => onHitl("reject")}
                        disabled={loading}
                        style={{ backgroundColor: "#b91c1c", color: "#fff" }}
                      >
                        Submit Rejection (Spawn Child Run)
                      </button>
                    </div>
                  </div>
                )}

                {/* Manual Override Panel */}
                {overrideMode && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "14px",
                      backgroundColor: "#eff6ff",
                      border: "1px solid #60a5fa",
                      borderRadius: "8px",
                    }}
                  >
                    <h4 style={{ margin: "0 0 8px 0", color: "#1e40af" }}>Manual Allocation Override</h4>
                    <p style={{ fontSize: "0.85rem", color: "#1e3a8a", margin: "0 0 10px 0" }}>
                      Adjust quantities directly. All modifications are validated mathematically against MOQs, supplier capacities, and warehouse space.
                    </p>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {overrideAllocations.map((alloc, idx) => (
                        <div key={alloc.supplier_code} style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                          <span style={{ width: "90px", fontWeight: 600 }}>{alloc.supplier_code}:</span>
                          <input
                            type="number"
                            value={alloc.units}
                            onChange={(e) => {
                              const val = Number(e.target.value);
                              setOverrideAllocations((prev) =>
                                prev.map((item, i) => (i === idx ? { ...item, units: val } : item))
                              );
                            }}
                            style={{ width: "120px" }}
                          />
                          <span style={{ fontSize: "0.8rem", color: "#475569" }}>units</span>
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: "10px", display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                      <label style={{ fontSize: "0.85rem" }}>
                        <input
                          type="checkbox"
                          checked={ackBreach}
                          onChange={(e) => setAckBreach(e.target.checked)}
                          style={{ marginRight: "4px" }}
                        />
                        Acknowledge concentration / policy breach if present
                      </label>
                      <button
                        type="button"
                        onClick={() => onHitl("override")}
                        disabled={loading}
                        style={{ backgroundColor: "#1d4ed8", color: "#fff" }}
                      >
                        Validate &amp; Save Override
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}

            {!isPending && (
              <div
                style={{
                  marginTop: "10px",
                  padding: "12px 16px",
                  background: badge.bg,
                  border: `1px solid ${badge.border}`,
                  borderRadius: "8px",
                  color: badge.color,
                }}
              >
                <strong>{badge.label}</strong> by{" "}
                <strong>{result.validation?.hitl_planner || "Authorized Reviewer"}</strong> —{" "}
                <em>"{result.validation?.hitl_comments || plannerComments}"</em>
              </div>
            )}
          </section>

          {/* ── Explainable recommendation & Execution Steps ── */}
          {isApproved ? (
            <section className="panel" style={{ borderLeft: "4px solid #22c55e" }}>
              <h2>✅ Approved Recommendation &amp; Operational Execution Plan</h2>
              <pre className="reason">{result.explainable_recommendation?.reason || "Execution plan approved."}</pre>
              {result.explainable_recommendation?.execution_steps && (
                <div style={{ marginTop: "12px" }}>
                  <h4 style={{ marginBottom: 6 }}>Execution Steps:</h4>
                  <ul style={{ paddingLeft: 20 }}>
                    {result.explainable_recommendation.execution_steps.map((st, i) => (
                      <li key={i} style={{ marginBottom: 4 }}>{st}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          ) : (
            <section
              className="panel"
              style={{ borderLeft: "4px solid #d1d5db", opacity: 0.8 }}
            >
              <h2>🔒 Recommendation &amp; Execution Steps (Locked — Awaiting HITL Approval)</h2>
              <p className="hint">
                Server-side recommendation lock is active. Downstream action plans and purchase orders will unlock once a planner approves the plan above.
              </p>
            </section>
          )}

          {/* ── Retrieved evidence (Hybrid RAG) ── */}
          <section className="panel">
            <h2>Retrieved Policy Evidence (Hybrid RAG)</h2>
            <ul className="evidence">
              {(result.retrieved_evidence || []).map((e, i) => (
                <li key={i}>
                  <strong>{e.title}</strong>
                  <p>{e.snippet}</p>
                </li>
              ))}
            </ul>
          </section>

          {/* ── Decision Events Audit Log Timeline ── */}
          {result.events && result.events.length > 0 && (
            <section className="panel">
              <h2>Decision Audit Events (`decision_events` Append-Only Ledger)</h2>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Action</th>
                      <th>Actor</th>
                      <th>Timestamp</th>
                      <th>Payload Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.events.map((ev) => (
                      <tr key={ev.id}>
                        <td>#{ev.id}</td>
                        <td>
                          <span className="badge" style={{ background: "#e0e7ff", color: "#3730a3" }}>
                            {ev.action}
                          </span>
                        </td>
                        <td><strong>{ev.actor}</strong></td>
                        <td>{ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}</td>
                        <td style={{ fontSize: "0.82rem", fontFamily: "monospace" }}>
                          {JSON.stringify(ev.payload)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Agent trace & Validation Log ── */}
          <section className="panel">
            <h2>Agent Execution Trace &amp; Validation Log</h2>
            <ol style={{ paddingLeft: 20 }}>
              {(result.agent_trace || []).map((t, i) => (
                <li
                  key={i}
                  style={{
                    fontWeight: t.startsWith("HITL") ? 700 : 400,
                    color: t.startsWith("HITL") ? "#059669" : undefined,
                    marginBottom: 4,
                  }}
                >
                  {t}
                </li>
              ))}
            </ol>
            {result.validation?.issues?.length ? (
              <p className="hint" style={{ marginTop: 8, color: "#b91c1c" }}>
                Validation Issues: {result.validation.issues.join("; ")}
              </p>
            ) : null}
          </section>
        </>
      )}

      {/* ── Footer ── */}
      <footer style={{ marginTop: 32, textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
        SupplyChainAI v1.0-hardened · Multi-Agent Decision Intelligence with Google OR-Tools
      </footer>
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
      {sub && <div style={{ fontSize: "0.75rem", color: "#cbd5e1", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}
