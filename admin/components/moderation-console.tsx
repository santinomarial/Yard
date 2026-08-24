"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { availableActions, compactId, formatReason } from "../lib/moderation";
import {
  apiRequest,
  developmentAdminSignIn,
  type AdminResolutionAction,
  type AuditAction,
  type Dashboard,
  type Report,
  type ReportStatus,
  type ReportTarget,
} from "../lib/yard-api";

const tokenKey = "yard-admin-token";

const actionLabels: Record<AdminResolutionAction, string> = {
  dismiss: "Dismiss",
  remove_listing: "Remove listing",
  warn_user: "Warn user",
  suspend_user: "Suspend user",
};

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </article>
  );
}

export function ModerationConsole() {
  const [token, setToken] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [audit, setAudit] = useState<AuditAction[]>([]);
  const [targetFilter, setTargetFilter] = useState<ReportTarget | "">("");
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "">("open");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setToken(window.localStorage.getItem(tokenKey)), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const reportQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (targetFilter) params.set("target_type", targetFilter);
    if (statusFilter) params.set("status", statusFilter);
    return params.size ? `?${params.toString()}` : "";
  }, [statusFilter, targetFilter]);

  const refresh = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [nextDashboard, nextReports, nextAudit] = await Promise.all([
        apiRequest<Dashboard>("/admin/dashboard", token),
        apiRequest<Report[]>(`/admin/reports${reportQuery}`, token),
        apiRequest<AuditAction[]>("/admin/audit-log", token),
      ]);
      setDashboard(nextDashboard);
      setReports(nextReports);
      setAudit(nextAudit);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load moderation data.");
    }
  }, [reportQuery, token]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function signIn() {
    setBusy("sign-in");
    setError(null);
    try {
      const nextToken = await developmentAdminSignIn();
      window.localStorage.setItem(tokenKey, nextToken);
      setToken(nextToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setBusy(null);
    }
  }

  function signOut() {
    window.localStorage.removeItem(tokenKey);
    setToken(null);
    setDashboard(null);
    setReports([]);
    setAudit([]);
  }

  async function resolve(report: Report, action: AdminResolutionAction) {
    const destructive = action === "remove_listing" || action === "suspend_user";
    const notes = window.prompt(
      destructive ? "Add the evidence supporting this action:" : "Optional moderator note:",
    );
    if (destructive && !notes?.trim()) return;
    setBusy(report.id);
    setError(null);
    try {
      await apiRequest<Report>(`/admin/reports/${report.id}/resolve`, token!, {
        method: "POST",
        body: JSON.stringify({ action, notes: notes?.trim() || null }),
      });
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The action could not be completed.");
    } finally {
      setBusy(null);
    }
  }

  if (!token) {
    return (
      <main className="login-shell">
        <section className="login-card" aria-labelledby="login-title">
          <p className="eyebrow">Private operations</p>
          <h1 id="login-title">Yard Moderation</h1>
          <p>
            Review community reports and record policy decisions. The local sign-in below exists
            only when the API runs in development mode.
          </p>
          {error && <p className="error-banner">{error}</p>}
          <button className="primary-button" onClick={signIn} disabled={busy === "sign-in"}>
            {busy === "sign-in" ? "Signing in…" : "Use local moderator identity"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="console-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Yard operations</p>
          <h1>Moderation desk</h1>
        </div>
        <div className="topbar-actions">
          <button className="quiet-button" onClick={() => void refresh()}>
            Refresh
          </button>
          <button className="quiet-button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <section aria-labelledby="health-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Current state</p>
            <h2 id="health-title">Marketplace health</h2>
          </div>
        </div>
        <div className="metric-grid">
          <Metric label="Open reports" value={dashboard?.open_reports ?? 0} />
          <Metric label="Resolved today" value={dashboard?.reports_resolved_today ?? 0} />
          <Metric label="Active listings" value={dashboard?.active_listings ?? 0} />
          <Metric label="New users today" value={dashboard?.new_users_today ?? 0} />
          <Metric label="Completed exchanges" value={dashboard?.completed_exchanges ?? 0} />
          <Metric label="Moderation backlog" value={dashboard?.moderation_backlog ?? 0} />
        </div>
      </section>

      <section className="workspace" aria-labelledby="queue-title">
        <div className="queue-panel">
          <div className="section-heading queue-heading">
            <div>
              <p className="eyebrow">Community safety</p>
              <h2 id="queue-title">Report queue</h2>
            </div>
            <div className="filters">
              <label>
                Target
                <select
                  value={targetFilter}
                  onChange={(event) => setTargetFilter(event.target.value as ReportTarget | "")}
                >
                  <option value="">All</option>
                  <option value="listing">Listings</option>
                  <option value="user">Users</option>
                  <option value="message">Messages</option>
                </select>
              </label>
              <label>
                Status
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as ReportStatus | "")}
                >
                  <option value="">All</option>
                  <option value="open">Open</option>
                  <option value="in_review">In review</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </label>
            </div>
          </div>

          <div className="report-list">
            {reports.length === 0 && <p className="empty-state">No reports match these filters.</p>}
            {reports.map((report) => (
              <article className="report-card" key={report.id}>
                <div className="report-summary">
                  <span className={`severity severity-${report.severity}`}>{report.severity}</span>
                  <span className="target-label">{report.target_type}</span>
                  <time dateTime={report.created_at}>
                    {new Date(report.created_at).toLocaleString()}
                  </time>
                </div>
                <h3>{formatReason(report.reason)}</h3>
                <p>{report.details || "No additional detail was supplied."}</p>
                <dl className="identifiers">
                  <div>
                    <dt>Report</dt>
                    <dd title={report.id}>{compactId(report.id)}</dd>
                  </div>
                  <div>
                    <dt>Target</dt>
                    <dd title={report.target_id}>{compactId(report.target_id)}</dd>
                  </div>
                </dl>
                {report.status === "open" || report.status === "in_review" ? (
                  <div className="action-row">
                    {availableActions(report).map((action) => (
                      <button
                        key={action}
                        className={
                          action === "remove_listing" || action === "suspend_user"
                            ? "danger-button"
                            : "quiet-button"
                        }
                        disabled={busy === report.id}
                        onClick={() => void resolve(report, action)}
                      >
                        {actionLabels[action]}
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="resolved-label">Resolved: {report.resolution}</p>
                )}
              </article>
            ))}
          </div>
        </div>

        <aside className="audit-panel" aria-labelledby="audit-title">
          <p className="eyebrow">Accountability</p>
          <h2 id="audit-title">Audit log</h2>
          <ol className="audit-list">
            {audit.slice(0, 12).map((action) => (
              <li key={action.id}>
                <strong>{action.action_type.replaceAll("_", " ")}</strong>
                <span>
                  {action.target_type} · {compactId(action.target_id)}
                </span>
                <time dateTime={action.created_at}>
                  {new Date(action.created_at).toLocaleString()}
                </time>
              </li>
            ))}
            {audit.length === 0 && <li className="empty-state">No actions recorded.</li>}
          </ol>
        </aside>
      </section>

      <footer>
        Yard is an independent community marketplace and is not affiliated with or endorsed by
        Harvard University.
      </footer>
    </main>
  );
}
