import { describe, expect, it } from "vitest";

import { compareSections, formatDate, formatTaka, parseAmountInput, shortHash } from "@/lib/format";

describe("parseAmountInput", () => {
  it("reads plain numbers, separators and currency text", () => {
    expect(parseAmountInput("3000")).toBe(3000);
    expect(parseAmountInput("Tk 15,000")).toBe(15000);
    expect(parseAmountInput(" 7 000 ")).toBe(7000);
  });
  it("reads Bangla digits", () => {
    expect(parseAmountInput("৩,০০০")).toBe(3000);
  });
  it("returns undefined for empty or non-numeric input", () => {
    expect(parseAmountInput("")).toBeUndefined();
    expect(parseAmountInput("abc")).toBeUndefined();
  });
});

describe("formatters", () => {
  it("formats Taka with separators", () => {
    expect(formatTaka(15000)).toBe("Tk 15,000");
    expect(formatTaka(null)).toBe("-");
  });
  it("treats timestamps without a zone as UTC", () => {
    expect(formatDate("2026-10-12T23:30:00")).toMatch(/Oct 2026/);
    expect(formatDate(null)).toBe("-");
    expect(formatDate("garbage")).toBe("-");
  });
  it("shortens hashes", () => {
    expect(shortHash("a".repeat(64))).toBe(`${"a".repeat(8)}…${"a".repeat(6)}`);
    expect(shortHash(null)).toBe("-");
  });
  it("orders sections numerically with sub-sections", () => {
    expect(["90", "89(2)", "100", "89(1)", "66"].sort(compareSections)).toEqual(["66", "89(1)", "89(2)", "90", "100"]);
  });
});
