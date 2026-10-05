# SupplyChainAI — 5-Minute Live Demonstration Script

This script walks through the core capabilities of SupplyChainAI in under 5 minutes for examiners, reviewers, and stakeholders.

---

## Pre-Demo Setup Check (30 seconds)

1. Verify backend and frontend are running:
   - Backend: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) (Status: `ok`)
   - Frontend: [http://localhost:5173](http://localhost:5173)
2. Ensure you have the reviewer API key ready: `secret_key_123` (Lead Planner) or `key_alice` (Alice).

---

## Step 1: Natural Language Planning Query (1 Minute)

1. Open the UI at [http://localhost:5173](http://localhost:5173).
2. Type into the query box:
   ```text
   Procure 10,000 units of Product A with low risk
   ```
3. Click **"Run Planning Pipeline"**.
4. **Highlight to the Examiner:**
   - **Multi-Agent Flow:** Observe the 5 specialist agents executing in sequence.
   - **Net Requirement Calculation:** Stock available across DCs is evaluated; net requirement is calculated as `max(0, Demand + SafetyStock - Available)`.
   - **MILP Optimization:** OR-Tools solves the allocation across suppliers and shipping lanes.
   - **Server-Side Recommendation Lock:** Note that while the plan is in `PENDING` status, raw purchase execution steps are locked until authenticated human sign-off.

---

## Step 2: Policy Explanation & Faithfulness (30 Seconds)

1. Scroll to the **Explainability Pane**.
2. **Highlight to the Examiner:**
   - The LLM explanation synthesizes the solver's decisions and cites corporate safety stock and low-risk policies retrieved via Hybrid RAG.
   - **Faithfulness Guard:** Every number in the explanation is verified against actual database facts. If hallucinated numbers are detected, the system safely falls back to a verified deterministic template.

---

## Step 3: Human-in-the-Loop Approval & Audit Timeline (45 Seconds)

1. Enter Reviewer Key: `secret_key_123` and select **"Approve Plan"**.
2. **Highlight to the Examiner:**
   - The status updates to `APPROVED`.
   - The execution steps unlock.
   - The **Audit Timeline** at the bottom updates with an immutable `APPROVE` record in `decision_events`, capturing the timestamp, actor identity (`lead_planner`), and run ID.

---

## Step 4: What-If Stress Testing (45 Seconds)

1. Navigate to the **"What-If Scenario Simulation"** section.
2. Select the scenario: **"Supplier Failure (SUP-C Outage)"**.
3. Click **"Run Scenario"**.
4. **Highlight to the Examiner:**
   - Side-by-side comparative table showing Baseline vs. Scenario.
   - Observe how the solver dynamically re-routes procurement to alternate vendors (e.g., SUP-A, SUP-B) while respecting supplier capacity limits and MOQs.
   - Note the separate reporting of `plan_risk` and `disruption_exposure`.

---

## Step 5: Structured Rejection & Lineage (45 Seconds)

1. Select **"Reject Plan"**.
2. Check the structured reason: `Exclude Supplier: SUP-A` and enter a comment: *"SUP-A currently undergoing factory audit."*
3. Click **"Submit Rejection"**.
4. **Highlight to the Examiner:**
   - The system records a `REJECT` event and automatically spins up a child simulation run linked via `parent_run_id`.
   - The child run completely excludes SUP-A from the allocation without manual re-entry.

---

## Step 6: Full-Fidelity Override & Mathematical Validation (45 Seconds)

1. On the child run, select **"Manual Override"**.
2. Attempt to input an allocation that violates a Minimum Order Quantity (e.g., 50 units for a supplier with MOQ of 500).
3. Click **"Validate & Apply Override"**.
4. **Highlight to the Examiner:**
   - The system rejects the invalid allocation with a clear constraint violation error (`MOQ breach`).
   - Now input a valid alternative allocation. The system calculates the exact `cost_delta_vs_optimal`, verifies feasibility, and records the `OVERRIDE` event.

---

## Summary Wrap-Up (15 Seconds)
*"To conclude: SupplyChainAI provides the intuitive conversational interface of modern generative AI, but grounds every operational number in mathematical MILP optimization, verifiable RAG policies, and enterprise-grade HITL governance."*
