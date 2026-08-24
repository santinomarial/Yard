import type { AdminResolutionAction, Report } from "./yard-api";

const labels: Record<string, string> = {
  prohibited_item: "Prohibited item",
  scam_fraud: "Scam or fraud",
  harassment: "Harassment",
  inappropriate_content: "Inappropriate content",
  counterfeit_stolen: "Counterfeit or stolen goods",
  spam: "Spam",
  other: "Other",
};

export function formatReason(reason: string): string {
  return labels[reason] ?? reason.replaceAll("_", " ");
}

export function availableActions(report: Report): AdminResolutionAction[] {
  const actions: AdminResolutionAction[] = ["dismiss", "warn_user", "suspend_user"];
  if (report.target_type === "listing") actions.splice(1, 0, "remove_listing");
  return actions;
}

export function compactId(id: string): string {
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}
