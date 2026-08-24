export type ReportTarget = "listing" | "user" | "message";
export type ReportStatus = "open" | "in_review" | "resolved" | "dismissed";
export type AdminResolutionAction =
  | "dismiss"
  | "remove_listing"
  | "warn_user"
  | "suspend_user";

export interface Dashboard {
  open_reports: number;
  reports_resolved_today: number;
  active_listings: number;
  new_users_today: number;
  completed_exchanges: number;
  moderation_backlog: number;
}

export interface Report {
  id: string;
  reporter_id: string;
  target_type: ReportTarget;
  target_id: string;
  reason: string;
  severity: "low" | "medium" | "high";
  details: string | null;
  status: ReportStatus;
  assigned_admin_id: string | null;
  resolution: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditAction {
  id: string;
  admin_id: string;
  report_id: string | null;
  action_type: string;
  target_type: string;
  target_id: string;
  notes: string | null;
  created_at: string;
}

interface ApiErrorEnvelope {
  error?: { code?: string; message?: string };
}

const apiBase = (
  process.env.NEXT_PUBLIC_YARD_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export async function apiRequest<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorEnvelope;
    throw new Error(payload.error?.message ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function developmentAdminSignIn(): Promise<string> {
  const response = await fetch(`${apiBase}/auth/development`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: "Local Yard Moderator", role: "admin" }),
  });
  if (!response.ok) throw new Error("Local moderator sign-in is unavailable.");
  const payload = (await response.json()) as { access_token: string };
  return payload.access_token;
}
