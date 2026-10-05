import { FormEvent, useEffect, useState } from "react";
import { createDecision, DecisionResponse, executeHitlAction, fetchCatalog, runWhatIf } from "./api/client";

const EXAMPLE =
  "I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk.";

function money(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

/** Colour + label for each HITL lifecycle state. */
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
  const [plannerName, setPlannerName] = useState("Sarah Connor (Lead Planner)");
  const [plannerComments, setPlannerComments] = useState("Verified constraints & supplier lead times");

  useEffect(() => {
    fetchCatalog()
      .then((c) => {
        const products = (c.products || []).map((p: { sku: string }) => p.sku).join(", ");
        setCatalog(products);
      })
      .catch(() => setCatalog("API not reachable yet"));
  }, []);

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
      setResult(
        await executeHitlAction({
          run_id: result.run_id,
          action,
          planner_name: plannerName,
          comments: plannerComments,
        })
      );
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

  return (
    <div className="page">
      <header>
        <div>
          <p className="eyebrow">Multi-agent decision intelligence</p>
          <h1>SupplyChainAI</h1>
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
          {/* ── KPIs (always visible) ── */}
          <section className="kpis">
            <Kpi label="Forecast" value={String(result.demand_forecast.forecast_units ?? "—")} />
            <Kpi label="Total cost" value={money(result.total_cost)} />
            <Kpi label="Delivery (h)" value={String(result.delivery_time_hours ?? "—")} />
            <Kpi label="Risk score" value={String(result.risk_score ?? "—")} />
            <Kpi label="Solver" value={result.optimization_status || "—"} />
          </section>

          {/* ── Supplier Allocation + Routes (always visible) ── */}
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
                      <td>{s.units.toLocaleString()}</td>
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
                  {result.routes.map((r) => (
                    <tr key={r.route_code + r.warehouse_code}>
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
              Available {result.inventory_plan.total_available ?? "—"} · net buy{" "}
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
            <h2>What-if</h2>
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
                  ⚠️ <strong>This plan requires human planner approval before the recommendation
                  can be finalised.</strong> Review the allocations, routes, costs, and risk
                  score above, then approve or reject.
                </p>
                <div className="row wrap" style={{ gap: "8px", marginTop: "8px" }}>
                  <input
                    value={plannerName}
                    onChange={(e) => setPlannerName(e.target.value)}
                    placeholder="Planner Name / Designation"
                    style={{ minWidth: "220px" }}
                  />
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
                    onClick={() => onHitl("reject")}
                    disabled={loading}
                    style={{ backgroundColor: "#dc2626", color: "#fff" }}
                  >
                    ❌ Reject &amp; re-optimise
                  </button>
                </div>
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
                {hitlStatus === "REJECTED" && (
                  <p style={{ margin: "8px 0 0", fontWeight: 600 }}>
                    🔄 Re-optimisation triggered — new plan generated above.
                  </p>
                )}
              </div>
            )}
          </section>

          {/* ── Explainable recommendation — GATED behind HITL approval ── */}
          {isApproved ? (
            <section className="panel" style={{ borderLeft: "4px solid #22c55e" }}>
              <h2>✅ Approved recommendation</h2>
              <pre className="reason">{result.explainable_recommendation.reason}</pre>
            </section>
          ) : (
            <section
              className="panel"
              style={{ borderLeft: "4px solid #d1d5db", opacity: 0.6 }}
            >
              <h2>🔒 Recommendation (locked — awaiting HITL approval)</h2>
              <p className="hint">
                The detailed recommendation will be unlocked after a planner
                approves the plan above.
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

          {/* ── Agent trace + HITL audit log ── */}
          <section className="panel">
            <h2>Agent trace &amp; HITL audit log</h2>
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
              <p className="hint">Validation: {result.validation.issues.join("; ")}</p>
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
