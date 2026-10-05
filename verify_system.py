import json
import time
import urllib.request

def run_verification():
    print("=" * 70)
    print(" SupplyChainAI - Comprehensive System Verification Suite")
    print("=" * 70)

    # 1. Health
    h_res = urllib.request.urlopen("http://localhost:8000/api/v1/health")
    health = json.loads(h_res.read().decode("utf-8"))
    print(f"\n[1/5] Health Check: status={health.get('status')}")
    print(f"      Database connected: {health.get('database')}")
    print(f"      LLM Provider: {health.get('llm_provider')}")
    print(f"      Solver: {health.get('solver')}")
    assert health["status"] == "ok"
    assert health["database"] is True

    # 2. Catalog
    c_res = urllib.request.urlopen("http://localhost:8000/api/v1/catalog")
    catalog = json.loads(c_res.read().decode("utf-8"))
    prods = catalog.get("products", [])
    sups = catalog.get("suppliers", [])
    whs = catalog.get("warehouses", [])
    print(f"\n[2/5] Catalog Check: {len(prods)} products, {len(sups)} suppliers, {len(whs)} warehouses")
    assert len(prods) == 10
    assert len(sups) == 7
    assert len(whs) == 4

    # 3. Decision Run (Baseline)
    query_text = "I need 10,000 units of Product A next month. Find the lowest-cost supply plan with low risk."
    req_data = json.dumps({"query": query_text}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/decisions",
        data=req_data,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    res = urllib.request.urlopen(req)
    d_time = time.time() - t0
    decision = json.loads(res.read().decode("utf-8"))
    run_id = decision["run_id"]

    print(f"\n[3/5] Decision Planning Query: Run #{run_id} completed in {d_time:.3f}s")
    print(f"      Statistical Forecast: {decision['demand_forecast']['forecast_units']:,} units ({decision['demand_forecast']['method']})")
    print(f"      Demand to meet: {decision['demand_forecast']['demand_to_meet']:,} units")
    print(f"      Inventory on hand: total available {decision['inventory_plan']['total_available']:,}, net req {decision['inventory_plan']['net_requirement']:,}")
    print(f"      Solver Status: {decision['optimization_status']}")
    print(f"      Total Optimized Cost: ${decision['total_cost']:,.2f}")
    print(f"      Delivery Lead Time: {decision['delivery_time_hours']} hours")
    print(f"      Composite Risk Score: {decision['risk_score']}/100")
    print(f"      Allocations ({len(decision['supplier_allocation'])} suppliers):")
    for s in decision["supplier_allocation"]:
        print(f"        * {s['supplier_code']} ({s['supplier_name']}): {s['units']:,} units -> ${s['cost']:,.2f}")
    print(f"      RAG Evidence: {len(decision['retrieved_evidence'])} chunks retrieved from pgvector")
    for ev in decision["retrieved_evidence"][:2]:
        print(f"        * \"{ev['title']}\" (score: {ev['score']:.4f})")
    print(f"      Agent Execution Trace: {' -> '.join(decision['agent_trace'][:5])}...")

    assert decision["optimization_status"] in {"OPTIMAL", "FEASIBLE"}
    assert decision["total_cost"] > 0
    assert len(decision["supplier_allocation"]) > 0

    # 4. What-If Scenario: Supplier Failure
    whatif_data = json.dumps({
        "run_id": run_id,
        "scenario": "supplier_failure",
        "supplier_code": "SUP-C"
    }).encode("utf-8")
    req_wi = urllib.request.Request(
        "http://localhost:8000/api/v1/what-if",
        data=whatif_data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    res_wi = urllib.request.urlopen(req_wi)
    wi_time = time.time() - t0
    whatif = json.loads(res_wi.read().decode("utf-8"))

    print(f"\n[4/5] What-If Stress-Test (Supplier Failure 'SUP-C'): Completed in {wi_time:.3f}s")
    comp = whatif["what_if"]["comparison"]
    print(f"      Baseline Cost : ${comp['total_cost']['baseline']:,.2f}")
    print(f"      Scenario Cost : ${comp['total_cost']['scenario']:,.2f}")
    print(f"      Cost Delta    : +${comp['total_cost']['delta']:,.2f}")
    print(f"      Risk Score    : {comp['risk_score']['baseline']} -> {comp['risk_score']['scenario']} (Delta: {comp['risk_score']['delta']:+})")

    scenario_suppliers = [a["supplier_code"] for a in whatif["supplier_allocation"]]
    assert "SUP-C" not in scenario_suppliers
    print(f"      Allocation Shifts: SUP-C excluded. New suppliers: {', '.join(scenario_suppliers)}")

    # 5. Frontend Dev Server Check
    f_res = urllib.request.urlopen("http://localhost:5173")
    assert f_res.status == 200
    html = f_res.read().decode("utf-8")
    assert "SupplyChainAI" in html
    print(f"\n[5/5] Frontend Service: Accessible at http://localhost:5173 (Status: 200 OK)")

    print("\n" + "=" * 70)
    print(" VERIFICATION RESULT: ALL 5/5 SUBSYSTEM CHECKS PASSED PERFECTLY")
    print("=" * 70)
    return {
        "health": health,
        "catalog_counts": {"products": len(prods), "suppliers": len(sups), "warehouses": len(whs)},
        "decision": decision,
        "whatif": whatif,
        "d_time": d_time,
        "wi_time": wi_time,
    }

if __name__ == "__main__":
    run_verification()
