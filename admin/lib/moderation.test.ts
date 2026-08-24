import { describe, expect, it } from "vitest";

import { availableActions, compactId, formatReason } from "./moderation";
import type { Report } from "./yard-api";

const report: Report = {
  id: "00000000-0000-0000-0000-000000000001",
  reporter_id: "00000000-0000-0000-0000-000000000002",
  target_type: "listing",
  target_id: "00000000-0000-0000-0000-000000000003",
  reason: "counterfeit_stolen",
  severity: "medium",
  details: null,
  status: "open",
  assigned_admin_id: null,
  resolution: null,
  resolved_at: null,
  created_at: "2026-08-24T12:00:00Z",
  updated_at: "2026-08-24T12:00:00Z",
};

describe("moderation presentation", () => {
  it("offers listing-specific takedown action", () => {
    expect(availableActions(report)).toContain("remove_listing");
    expect(availableActions({ ...report, target_type: "message" })).not.toContain(
      "remove_listing",
    );
  });

  it("formats policy reasons and identifiers", () => {
    expect(formatReason("counterfeit_stolen")).toBe("Counterfeit or stolen goods");
    expect(compactId(report.id)).toBe("00000000…0001");
  });
});
