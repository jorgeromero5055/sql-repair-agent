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

export async function listRepairs(): Promise<RepairListItem[]> {
  const response = await fetch(`${BASE}/repairs`);
  if (!response.ok) throw new Error(`list failed: ${response.status}`);
  return response.json();
}

export async function createRepair(intent: string, brokenQuery: string) {
  const response = await fetch(`${BASE}/repairs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, broken_query: brokenQuery }),
  });
  if (!response.ok) throw new Error(`create failed: ${response.status}`);
  return response.json();
}
