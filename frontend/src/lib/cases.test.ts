import { describe, expect, it } from "vitest";

import { groupOf, RESULT_GROUPS } from "@/constants/status";
import { buildLimitations, buildReferences, capitalize, countGroups, firstName, shortUrl } from "@/lib/cases";
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
    manual_input: {}, receipt: null, dataset: null, matched_rule: null, matches: [], exception_checks: [], analysis: null, ...over,
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
