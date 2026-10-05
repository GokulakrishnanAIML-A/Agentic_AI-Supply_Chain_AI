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
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecisionResponse | null>(null);
  const [catalog, setCatalog] = useState<string>("");
  const [scenario, setScenario] = useState("supplier_failure");
  const [pct, setPct] = useState(20);
  const [supplierCode, setSupplierCode] = useState("SUP-C");

  // HITL & Auth State
  const [apiKey, setApiKey] = useState("secret_key_123");
  const [plannerComments, setPlannerComments] = useState("Verified constraints & supplier lead times");
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
      .catch(() => setCatalog("API not reachable yet"));
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
        override_allocs = overrideAllocations;
      }

      const res = await executeHitlAction({
        run_id: result.run_id,
        action,
        apiKey,
        comments: plannerComments,
        override_allocations: override_allocs,
        reject_reason,
        acknowledge_policy_breach: ackBreach,
      });
      setResult(res);
      setRejectMode(false);
      setOverrideMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const hitlStatus = result?.validation?.hitl_status as string | undefined;
  const isApproved = hitlStatus === "APPROVED" || hitlStatus === "APPROVED_WITH_OVERRIDE";
  const isPending = !hitlStatus || hitlStatus === "PENDING_REVIEW";
  const badge = hitlBadge(hitlStatus);

  const isDegraded = result?.validation?.degraded || result?.explainable_recommendation?.degraded;
  const relaxations = result?.validation?.relaxations || result?.explainable_recommendation?.relaxations_applied || [];
  const contracts = result?.explainable_recommendation?.llm_contracts || {};

  return (
    <div className="page">
      <header>
        <div>
          <p className="eyebrow">Multi-agent decision intelligence</p>
          <h1>SupplyChainAI</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label style={{ fontSize: "0.85rem", color: "#64748b" }}>Planner Identity / Key:</label>
          <select
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
          >
            <option value="secret_key_123">Lead Supply Planner (secret_key_123)</option>
            <option value="key_alice">Alice - Senior Planner (key_alice)</option>
            <option value="key_bob">Bob - Procurement Lead (key_bob)</option>
          </select>
        </div>
      </header>

      <form className="panel" onSubmit={onSubmit}>
        <label htmlFor="query">Natural-language supply-chain problem</label>
        <textarea id="query" value={query} onChange={(e) => setQuery(e.target.value)} rows={4} />
        <div className="row">
          <button type="submit" disabled={loading}>
            {loading ? "Planning…" : "Optimize supply plan"}
          </button>
          <p className="hint">Catalog: {catalog || "loading…"}</p>
        </div>
      </form>

      {error && <div className="error">{error}</div>}

      {result && (
        <>
          {/* ── Degraded Banner (T2.3) ── */}
          {isDegraded && (
            <div
              style={{
                backgroundColor: "#fff7ed",
                border: "2px solid #ea580c",
                borderRadius: "8px",
                padding: "14px 18px",
                marginBottom: "16px",
                color: "#9a3412",
              }}
            >
              <h3 style={{ margin: "0 0 6px 0", color: "#c2410c" }}>⚠️ Degraded Replan Mode Active</h3>
              <p style={{ margin: "0 0 8px 0" }}>
                Strict optimal constraints could not be satisfied. The system safely relaxed whitelisted parameters to find a viable feasible plan:
              </p>
              <ul>
                {relaxations.map((r, i) => (
                  <li key={i}>
                    <strong>{r.constraint}</strong>: relaxed from {r.before} to {r.after}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── KPIs (T1.5 Split Metrics) ── */}
          <section className="kpis">
            <Kpi label="Forecast" value={String(result.demand_forecast.forecast_units ?? "—")} />
            <Kpi label="Total Cost" value={money(result.total_cost)} />
            <Kpi label="Delivery (h)" value={String(result.delivery_time_hours ?? "—")} />
            <Kpi
              label="Plan Risk (Supplier)"
              value={result.validation?.plan_risk != null ? `${(result.validation.plan_risk * 100).toFixed(1)}%` : String(result.risk_score ?? "—")}
            />
            <Kpi
              label="Disruption Exposure (Env)"
              value={result.validation?.disruption_exposure != null ? `${(result.validation.disruption_exposure * 100).toFixed(1)}%` : "0.0%"}
            />
            <Kpi label="Solver Status" value={result.optimization_status || "—"} />
          </section>

          {/* ── LLM Guard Badges (T2.1) ── */}
          {Object.keys(contracts).length > 0 && (
            <section className="panel" style={{ padding: "10px 16px" }}>
              <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Pipeline Node Contracts:</span>
                {Object.entries(contracts).map(([node, c]) => (
                  <span
                    key={node}
                    style={{
                      fontSize: "0.75rem",
                      padding: "3px 8px",
                      borderRadius: "4px",
                      background: c.used_llm ? "#e0f2fe" : "#f1f5f9",
                      color: c.used_llm ? "#0369a1" : "#475569",
                      border: `1px solid ${c.used_llm ? "#7dd3fc" : "#cbd5e1"}`,
                    }}
                  >
                    {node}: {c.used_llm ? `🤖 LLM (${c.latency_ms}ms)` : `⚡ Deterministic (${c.fallback_reason || "Rule"})`}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* ── Supplier Allocation + Routes ── */}
          <div className="grid">
            <section className="panel">
              <h2>Supplier allocation</h2>
              <table>
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Units</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {result.supplier_allocation.map((s) => (
                    <tr key={s.supplier_code}>
                      <td>
                        {s.supplier_code} · {s.supplier_name}
                      </td>
                      <td>{(s.units ?? s.quantity ?? 0).toLocaleString()}</td>
                      <td>{money(s.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="panel">
              <h2>Routes</h2>
              <table>
                <thead>
                  <tr>
                    <th>Lane</th>
                    <th>Mode</th>
                    <th>Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {result.routes.map((r, i) => (
                    <tr key={i}>
                      <td>
                        {r.route_code} → {r.warehouse_code}
                      </td>
                      <td>{r.mode}</td>
                      <td>{r.quantity.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          {/* ── Inventory plan ── */}
          <section className="panel">
            <h2>Inventory plan</h2>
            <p>
              Available: {result.inventory_plan.total_available ?? "—"} · Net requirement:{" "}
              {result.inventory_plan.net_requirement ?? "—"}
            </p>
            <table>
              <thead>
                <tr>
                  <th>DC</th>
                  <th>On hand</th>
                  <th>Reserved</th>
                  <th>Available</th>
                  <th>Safety</th>
                </tr>
              </thead>
              <tbody>
                {(result.inventory_plan.rows || []).map((r) => (
                  <tr key={r.warehouse_code}>
                    <td>{r.warehouse_code}</td>
                    <td>{r.on_hand}</td>
                    <td>{r.reserved}</td>
                    <td>{r.available}</td>
                    <td>{r.safety_stock}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* ── What-if ── */}
          <section className="panel">
            <h2>What-if Scenarios</h2>
            <div className="row wrap">
              <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                <option value="demand_increase">Demand increase</option>
                <option value="supplier_failure">Supplier failure</option>
                <option value="price_increase">Price increase</option>
                <option value="fuel_increase">Fuel increase</option>
                <option value="route_disruption">Route disruption</option>
                <option value="inventory_shortage">Inventory shortage</option>
              </select>
              <input
                type="number"
                value={pct}
                onChange={(e) => setPct(Number(e.target.value))}
                title="Percent"
              />
              <input
                value={supplierCode}
                onChange={(e) => setSupplierCode(e.target.value)}
                title="Supplier code"
              />
              <button type="button" onClick={onWhatIf} disabled={loading}>
                Re-run scenario
              </button>
            </div>
            {result.what_if?.comparison && (
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
                      <td>{k}</td>
                      <td>{v.baseline}</td>
                      <td>{v.scenario}</td>
                      <td>{v.delta}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* ═══════════════════════════════════════════════════
              HUMAN-IN-THE-LOOP — MANDATORY DECISION GATE
              ═══════════════════════════════════════════════════ */}
          <section
            className="panel"
            style={{
              borderLeft: `4px solid ${badge.border}`,
              background: isPending ? "#fffbeb" : badge.bg,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2>Human-in-the-Loop (HITL) — Decision Gate</h2>
              <span
                style={{
                  padding: "4px 12px",
                  borderRadius: "999px",
                  fontSize: "0.8rem",
                  fontWeight: 700,
                  background: badge.bg,
                  color: badge.color,
                  border: `1.5px solid ${badge.border}`,
                }}
              >
                {badge.label}
              </span>
            </div>

            {isPending && (
              <>
                <p style={{ margin: "10px 0 6px", color: "#92400e" }}>
                  ⚠️ <strong>This plan requires authenticated human planner sign-off before recommendations and execution steps are unlocked.</strong>
                </p>
                <div className="row wrap" style={{ gap: "8px", marginTop: "8px" }}>
                  <input
                    value={plannerComments}
                    onChange={(e) => setPlannerComments(e.target.value)}
                    placeholder="Planner Review Comments"
                    style={{ flex: 1, minWidth: "260px" }}
                  />
                  <button
                    type="button"
                    onClick={() => onHitl("approve")}
                    disabled={loading}
                    style={{ backgroundColor: "#059669", color: "#fff" }}
                  >
                    ✅ Approve plan
                  </button>
                  <button
                    type="button"
                    onClick={() => setRejectMode(!rejectMode)}
                    style={{ backgroundColor: "#dc2626", color: "#fff" }}
                  >
                    ❌ {rejectMode ? "Cancel Reject" : "Reject & Re-plan…"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setOverrideMode(!overrideMode)}
                    style={{ backgroundColor: "#2563eb", color: "#fff" }}
                  >
                    ✏️ {overrideMode ? "Cancel Override" : "Manual Override…"}
                  </button>
                </div>

                {/* Structured Reject Drawer (T3.3) */}
                {rejectMode && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "14px",
                      backgroundColor: "#fef2f2",
                      border: "1px solid #f87171",
                      borderRadius: "6px",
                    }}
                  >
                    <h4 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>Structured Rejection &amp; Re-optimization</h4>
                    <p style={{ fontSize: "0.85rem", color: "#7f1d1d", margin: "0 0 10px 0" }}>
                      Specify constraints to guide the next optimization pass. Leaving constraints blank will record rejection without re-running.
                    </p>
                    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
                      <label style={{ fontSize: "0.85rem" }}>
                        Exclude Suppliers:
                        <input
                          placeholder="e.g. SUP-A, SUP-B"
                          onChange={(e) =>
                            setExcludeSupplierList(
                              e.target.value
                                .split(",")
                                .map((s) => s.trim())
                                .filter(Boolean)
                            )
                          }
                          style={{ marginLeft: "6px" }}
                        />
                      </label>
                      <label style={{ fontSize: "0.85rem" }}>
                        Max Single Share:
                        <input
                          type="number"
                          step="0.05"
                          min="0.1"
                          max="1.0"
                          placeholder="0.50"
                          onChange={(e) => setMaxShare(e.target.value ? Number(e.target.value) : undefined)}
                          style={{ width: "70px", marginLeft: "6px" }}
                        />
                      </label>
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
                        Submit Rejection
                      </button>
                    </div>
                  </div>
                )}

                {/* Manual Override Drawer (T3.4) */}
                {overrideMode && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "14px",
                      backgroundColor: "#eff6ff",
                      border: "1px solid #60a5fa",
                      borderRadius: "6px",
                    }}
                  >
                    <h4 style={{ margin: "0 0 8px 0", color: "#1e40af" }}>Manual Allocation Override</h4>
                    <p style={{ fontSize: "0.85rem", color: "#1e3a8a", margin: "0 0 10px 0" }}>
                      Adjust quantities directly. All changes are validated against supplier capacity, MOQ, and warehouse bounds.
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
                    <div style={{ marginTop: "10px", display: "flex", alignItems: "center", gap: "10px" }}>
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
                <strong>{result.validation?.hitl_planner}</strong> —{" "}
                <em>"{result.validation?.hitl_comments}"</em>
              </div>
            )}
          </section>

          {/* ── Explainable recommendation — GATED behind HITL approval (T3.5) ── */}
          {isApproved ? (
            <section className="panel" style={{ borderLeft: "4px solid #22c55e" }}>
              <h2>✅ Approved Recommendation &amp; Execution Plan</h2>
              <pre className="reason">{result.explainable_recommendation.reason}</pre>
              {result.explainable_recommendation.execution_steps && (
                <div style={{ marginTop: "12px" }}>
                  <h4>Execution Steps:</h4>
                  <ul>
                    {result.explainable_recommendation.execution_steps.map((st, i) => (
                      <li key={i}>{st}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          ) : (
            <section
              className="panel"
              style={{ borderLeft: "4px solid #d1d5db", opacity: 0.7 }}
            >
              <h2>🔒 Recommendation &amp; Execution Steps (Locked — Awaiting HITL Approval)</h2>
              <p className="hint">
                Server-side recommendation lock is active. Downstream action plans and purchase orders will unlock once a planner approves the plan above.
              </p>
            </section>
          )}

          {/* ── Retrieved evidence ── */}
          <section className="panel">
            <h2>Retrieved evidence</h2>
            <ul className="evidence">
              {result.retrieved_evidence.map((e, i) => (
                <li key={i}>
                  <strong>{e.title}</strong>
                  <p>{e.snippet}</p>
                </li>
              ))}
            </ul>
          </section>

          {/* ── Decision Events Audit Log Timeline (T3.1) ── */}
          {result.events && result.events.length > 0 && (
            <section className="panel">
              <h2>Decision Audit Events (Append-Only Log)</h2>
              <table>
                <thead>
                  <tr>
                    <th>Event ID</th>
                    <th>Action</th>
                    <th>Actor</th>
                    <th>Timestamp</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {result.events.map((ev) => (
                    <tr key={ev.id}>
                      <td>#{ev.id}</td>
                      <td>
                        <strong>{ev.action}</strong>
                      </td>
                      <td>{ev.actor}</td>
                      <td>{ev.created_at ? new Date(ev.created_at).toLocaleString() : "—"}</td>
                      <td style={{ fontSize: "0.85rem", fontFamily: "monospace" }}>
                        {JSON.stringify(ev.payload)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* ── Agent trace ── */}
          <section className="panel">
            <h2>Agent Trace &amp; Validation Log</h2>
            <ol>
              {result.agent_trace.map((t, i) => (
                <li
                  key={i}
                  style={{
                    fontWeight: t.startsWith("HITL") ? 700 : 400,
                    color: t.startsWith("HITL") ? "#059669" : undefined,
                  }}
                >
                  {t}
                </li>
              ))}
            </ol>
            {result.validation?.issues?.length ? (
              <p className="hint">Validation Issues: {result.validation.issues.join("; ")}</p>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
