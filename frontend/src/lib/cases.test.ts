import { describe, expect, it } from "vitest";

import { groupOf, RESULT_GROUPS } from "@/constants/status";
import { buildLimitations, buildReferences, capitalize, countGroups, describeScoreLine, describeScoreReason, firstName, shortUrl } from "@/lib/cases";
import type { CaseDetail, ValidationStatus } from "@/types/api";

describe("groupOf", () => {
  it("maps every status to one of the three groups", () => {
    const expected: Record<ValidationStatus, keyof typeof RESULT_GROUPS> = {
      VALID: "consistent",
      INVALID_FINE_TOO_HIGH: "review",
      INVALID_REASON_MISMATCH: "review",
      VALID_BUT_EXCEPTION_POSSIBLE: "review",
      INVALID_EXCEPTION_NOT_APPLICABLE: "review",
      NEEDS_MANUAL_REVIEW: "insufficient",
      PENDING_ANALYSIS: "insufficient",
    };
    for (const [status, group] of Object.entries(expected)) expect(groupOf(status as ValidationStatus)).toBe(group);
  });
});

describe("countGroups", () => {
  it("counts each group and the total", () => {
    const cases = ["VALID", "VALID", "INVALID_FINE_TOO_HIGH", "NEEDS_MANUAL_REVIEW", "VALID_BUT_EXCEPTION_POSSIBLE"].map((s) => ({ validation_status: s as ValidationStatus }));
    expect(countGroups(cases)).toEqual({ all: 5, consistent: 2, review: 2, insufficient: 1 });
  });
  it("handles no cases", () => {
    expect(countGroups([])).toEqual({ all: 0, consistent: 0, review: 0, insufficient: 0 });
  });
});

describe("small helpers", () => {
  it("capitalises without touching the rest", () => {
    expect(capitalize("over speed")).toBe("Over speed");
    expect(capitalize("")).toBe("");
    expect(capitalize(null)).toBe("");
  });
  it("takes the first name", () => {
    expect(firstName("Rafiq Nahid")).toBe("Rafiq");
    expect(firstName("  Aisha  ")).toBe("Aisha");
    expect(firstName(null)).toBe("");
  });
  it("shortens long addresses in the middle and leaves short ones alone", () => {
    expect(shortUrl("https://www.example.com/notice/1")).toBe("example.com/notice/1");
    const long = shortUrl("https://example.com/traffic-fine-notices/2026/10/very-long-reference-number-0410");
    expect(long.length).toBeLessThanOrEqual(32);
    expect(long).toContain("…");
    expect(shortUrl("not a url")).toBe("not a url");
  });
});

function caseWith(over: Partial<CaseDetail> = {}, extracted: Partial<CaseDetail["extracted"]> = {}): CaseDetail {
  return {
    id: "c1", created_at: "2026-10-12T10:00:00", updated_at: "2026-10-12T10:00:00", case_source: "manual_entry", dummy_url: null,
    validation_status: "VALID", validation_summary: "", ai_explanation: "", confidence_score: 90,
    extracted: { reason: "speeding", amount: 3000, date: "2026-10-12", location: "Dhaka", vehicle_type: "car", receipt_number: "A1", section: "87", notes: null, ...extracted },
    manual_input: {}, receipt: null, dataset: null, matched_rule: null, matches: [], exception_checks: [], analysis: null, audit: { enabled: true, status: "not_recorded", latest: null, records: 0 }, ...over,
  };
}

describe("buildLimitations", () => {
  it("always ends with the two standing caveats", () => {
    const l = buildLimitations(caseWith());
    expect(l.at(-1)).toMatch(/not an authoritative legal determination/);
    expect(l.at(-2)).toMatch(/not been verified against the official Act/);
    expect(l).toHaveLength(2);
  });
  it("names every missing detail", () => {
    const l = buildLimitations(caseWith({}, { amount: null, section: null, vehicle_type: null, date: null, location: null, receipt_number: null }));
    expect(l.join(" ")).toMatch(/No fine amount/);
    expect(l.join(" ")).toMatch(/No section was cited/);
    expect(l.join(" ")).toMatch(/No vehicle type/);
    expect(l.join(" ")).toMatch(/date, location, receipt number/);
  });
  it("says a sample notice was not read from the entered URL", () => {
    expect(buildLimitations(caseWith({ case_source: "dummy_url" })).join(" ")).toMatch(/illustrative sample notice/);
  });
});

describe("buildReferences", () => {
  it("is empty when nothing matched", () => {
    expect(buildReferences(caseWith())).toEqual([]);
  });
});

import { auditStatusMeta, canRecord, integrityMeta, verifyMeta } from "@/lib/audit";
import type { AuditSummary } from "@/types/api";

const audit = (over: Partial<AuditSummary> = {}): AuditSummary => ({ enabled: true, status: "not_recorded", latest: null, records: 0, ...over });

describe("audit labels", () => {
  it("describes each record state", () => {
    expect(auditStatusMeta(audit({ status: "sealed", records: 1 })).tone).toBe("ok");
    expect(auditStatusMeta(audit({ status: "pending" })).tone).toBe("warn");
    expect(auditStatusMeta(audit({ status: "failed" })).tone).toBe("bad");
    expect(auditStatusMeta(audit({ enabled: false })).label).toBe("Auditing off");
  });
  it("offers Record now only when there is something to record and auditing is on", () => {
    expect(canRecord(audit({ status: "pending" }))).toBe(true);
    expect(canRecord(audit({ status: "failed" }))).toBe(true);
    expect(canRecord(audit({ status: "not_recorded" }))).toBe(true);
    expect(canRecord(audit({ status: "sealed" }))).toBe(false);
    expect(canRecord(audit({ enabled: false, status: "not_recorded" }))).toBe(false);
  });
  it("shows a mismatch as a failure and a missing record as a warning", () => {
    expect(verifyMeta("mismatch").tone).toBe("bad");
    expect(verifyMeta("verified").tone).toBe("ok");
    expect(verifyMeta("not_on_chain").tone).toBe("warn");
    expect(verifyMeta("unavailable").tone).toBe("neutral");
  });
  it("labels the dataset integrity states", () => {
    expect(integrityMeta("verified").tone).toBe("ok");
    expect(integrityMeta("tampered").tone).toBe("bad");
    expect(integrityMeta("unanchored").tone).toBe("warn");
  });
});

describe("describeScoreReason", () => {
  it("rewrites the engine's score notes as plain sentences", () => {
    expect(describeScoreReason("exact alias “exceeding speed limit” +40")).toBe("Offence text is exactly “exceeding speed limit” (+40)");
    expect(describeScoreReason("partial alias “fitness” +30")).toBe("Offence text partly matches “fitness” (+30)");
    expect(describeScoreReason("keywords speed +20, speed limit +25")).toBe("Key words found: speed (+20), speed limit (+25)");
    expect(describeScoreReason("cited section +50")).toBe("Receipt cites this section number (+50)");
    expect(describeScoreReason("best reason score 20, threshold 30")).toContain("at least 30 is needed");
    expect(describeScoreReason("allowed_fine = max_fine = 10000")).toBe("Allowed amount is the section's maximum: Tk 10,000");
    expect(describeScoreReason("max_fine = None, min_fine = 0")).toBe("Fine limit: no Taka ceiling");
  });

  it("leaves anything it does not recognise as it was, and splits a whole line", () => {
    expect(describeScoreReason("Road Transport Act s.87")).toBe("Road Transport Act s.87");
    expect(describeScoreLine("exact alias “a” +40 · cited section +50")).toHaveLength(2);
  });
});
