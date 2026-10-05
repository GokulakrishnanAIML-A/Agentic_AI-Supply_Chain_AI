export type DecisionResponse = {
  run_id: number;
  query: string;
  demand_forecast: {
    product?: string;
    sku?: string;
    forecast_units?: number;
    method?: string;
    history?: { month: string; quantity: number }[];
    requested_quantity?: number | null;
    demand_to_meet?: number;
  };
  supplier_allocation: { supplier_code: string; supplier_name: string; units: number; cost: number; quantity?: number; unit_price?: number }[];
  routes: {
    supplier_code: string;
    warehouse_code: string;
    route_code: string;
    mode: string;
    quantity: number;
    line_cost: number;
    transit_hours: number;
    lead_time_days: number;
  }[];
  inventory_plan: {
    rows?: {
      warehouse_code: string;
      on_hand: number;
      reserved: number;
      available: number;
      safety_stock: number;
    }[];
    total_available?: number;
    net_requirement?: number;
  };
  total_cost: number | null;
  delivery_time_hours: number | null;
  risk_score: number | null;
  optimization_status: string | null;
  retrieved_evidence: { title: string; snippet: string; score: number; source_path?: string }[];
  explainable_recommendation: {
    reason?: string;
    summary?: string;
    execution_steps?: string[];
    execution_locked?: boolean;
    degraded?: boolean;
    relaxations_applied?: { constraint: string; before: number; after: number }[];
    llm_contracts?: Record<string, { used_llm: boolean; latency_ms: number; fallback_reason?: string }>;
  };
  agent_trace: string[];
  validation: {
    ok?: boolean;
    issues?: string[];
    hitl_status?: string;
    hitl_planner?: string;
    hitl_comments?: string;
    degraded?: boolean;
    relaxations?: { constraint: string; before: number; after: number }[];
    plan_risk?: number;
    disruption_exposure?: number;
  };
  events?: { id: number; actor: string; action: string; payload: Record<string, any>; created_at: string }[];
  execution_locked?: boolean;
  what_if?: {
    label?: string;
    comparison?: Record<string, { baseline: number; scenario: number; delta: number }>;
  } | null;
  data_disclaimer: string;
};

const API = import.meta.env.VITE_API_BASE || "";

export async function createDecision(query: string): Promise<DecisionResponse> {
  const res = await fetch(`${API}/api/v1/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function runWhatIf(body: {
  run_id: number;
  scenario: string;
  pct?: number;
  supplier_code?: string;
  route_code?: string;
}): Promise<DecisionResponse> {
  const res = await fetch(`${API}/api/v1/what-if`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchCatalog() {
  const res = await fetch(`${API}/api/v1/catalog`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function executeHitlAction(
  arg1: number | {
    run_id: number;
    action: string;
    apiKey?: string;
    comments?: string;
    override_allocations?: any[];
    reject_reason?: {
      exclude_suppliers?: string[];
      max_supplier_share?: number;
      force_low_risk?: boolean;
      comment?: string;
    };
    acknowledge_policy_breach?: boolean;
  },
  actionArg?: string,
  apiKeyArg?: string,
  commentsArg?: string,
  rejectReasonArg?: any,
  overrideAllocsArg?: any,
  ackBreachArg?: boolean
): Promise<DecisionResponse> {
  let run_id: number;
  let action: string;
  let apiKey: string;
  let comments: string;
  let override_allocations: any[] | undefined;
  let reject_reason: any | undefined;
  let acknowledge_policy_breach: boolean;

  if (typeof arg1 === "object" && arg1 !== null) {
    run_id = arg1.run_id;
    action = arg1.action;
    apiKey = arg1.apiKey || "secret_key_123";
    comments = arg1.comments || "Reviewed by human planner";
    override_allocations = arg1.override_allocations;
    reject_reason = arg1.reject_reason;
    acknowledge_policy_breach = arg1.acknowledge_policy_breach || false;
  } else {
    run_id = Number(arg1);
    action = actionArg || "approve";
    apiKey = apiKeyArg || "secret_key_123";
    comments = commentsArg || "Reviewed by human planner";
    reject_reason = rejectReasonArg;
    override_allocations = overrideAllocsArg;
    acknowledge_policy_breach = ackBreachArg || false;
  }

  if (isNaN(run_id) || !run_id) {
    throw new Error(`Invalid run_id: ${run_id}`);
  }

  const res = await fetch(`${API}/api/v1/decisions/${run_id}/hitl`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({
      action,
      comments,
      override_allocations,
      reject_reason,
      acknowledge_policy_breach,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
