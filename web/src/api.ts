const BASE = import.meta.env.VITE_API_URL;

export type RepairStatus =
  | "queued"
  | "running"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed";

export type RepairListItem = {
  id: string;
  intent: string;
  status: RepairStatus;
  created_at: string;
};

export type Statement = { sql: string; ok: boolean };

export type Attempt = {
  attempt: number;
  passed: boolean;
  reason: string | null;
  statements: Statement[];
};

export type Trace = {
  attempts: number;
  turns: number;
  tokens: number;
  passed: boolean;
  failure_reason: string | null;
  latency_ms: number | null;
};

export type Row = Record<string, string | number | boolean | null>;

// One repair, exactly as GET /repairs/{id} sends it back since v3 deliverable 4.
// trace, attempts and preview are the parts that deliverable added.
export type RepairDetail = {
  id: string;
  intent: string;
  broken_query: string;
  fixed_query: string | null;
  explanation: string | null;
  status: RepairStatus;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  trace: Trace | null;
  attempts: Attempt[];
  preview: Row[] | null;
};

// Every request goes through here. When the API refuses something it explains why in a
// "detail" field — reject needs a reason, this repair was already decided, and so on. We throw
// that message so the screen can show the server's own words instead of a status number.
// The rule about what's allowed lives on the server; this just repeats what it said.
async function send(path: string, options?: RequestInit) {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `request failed: ${response.status}`);
  }
  return response.json();
}

// POST with a JSON body. Used by everything that sends data rather than just asking for it.
const asJson = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function listRepairs(): Promise<RepairListItem[]> {
  return send("/repairs");
}

export function getRepair(id: string): Promise<RepairDetail> {
  return send(`/repairs/${id}`);
}

export function createRepair(intent: string, brokenQuery: string) {
  return send("/repairs", asJson({ intent, broken_query: brokenQuery }));
}

export function approveRepair(id: string) {
  return send(`/repairs/${id}/approve`, { method: "POST" });
}

export function rejectRepair(id: string, reason: string) {
  return send(`/repairs/${id}/reject`, asJson({ reason }));
}

export type BreakTypeStat = {
  break_type: string;
  cases: number;
  pass_at_1: number;
  pass_at_3: number;
};

export type RunFailure = {
  case_id: string;
  break_type: string;
  fixed_query: string | null;
  failure_reason: string | null;
};

export type RunSummary = {
  id: string;
  note: string | null;
  model: string;
  started_at: string;
  finished_at: string | null;
  cases: number;
  pass_at_1: number;
  pass_at_3: number;
  avg_attempts: number;
  avg_latency_ms: number | null;
  tokens: number;
  cost_usd: number;
};

export type RunDetail = RunSummary & {
  by_break_type: BreakTypeStat[];
  failures: RunFailure[];
};

export function listRuns(): Promise<RunSummary[]> {
  return send("/runs");
}

export function getRun(id: string): Promise<RunDetail> {
  return send(`/runs/${id}`);
}
