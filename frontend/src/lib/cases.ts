import { groupOf, type ResultGroup } from "@/constants/status";
import type { CaseDetail, CaseListItem } from "@/types/api";

export const capitalize = (s: string | null | undefined) => {
  const t = String(s ?? "");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

/** "example.com/notice/0410", shortened in the middle when long. */
export function shortUrl(u: string | null | undefined): string {
  let s = String(u ?? "");
  try {
    const x = new URL(s);
    s = x.host.replace(/^www\./, "") + (x.pathname === "/" ? "" : x.pathname) + x.search;
  } catch {
    /* keep the raw text */
  }
  return s.length > 34 ? `${s.slice(0, 22)}…${s.slice(-9)}` : s;
}

export function countGroups(cases: Pick<CaseListItem, "validation_status">[]): Record<ResultGroup | "all", number> {
  const n = { all: cases.length, consistent: 0, review: 0, insufficient: 0 };
  for (const c of cases) n[groupOf(c.validation_status)]++;
  return n;
}

export function firstName(fullName: string | null | undefined): string {
  return (fullName ?? "").trim().split(/\s+/)[0] ?? "";
}

/** Plain-language notes on what the result could not take into account. */
export function buildLimitations(c: CaseDetail): string[] {
  const x = c.extracted;
  const out: string[] = [];
  if (c.analysis?.manual_reason) out.push(c.analysis.manual_reason);
  if (x.amount == null) out.push("No fine amount was provided.");
  if (!x.section) out.push("No section was cited on the notice, so the section was inferred from the offence reason.");
  if (!x.vehicle_type) out.push("No vehicle type was provided, so vehicle-based exceptions could not be checked.");
  const missing = [!x.date && "date", !x.location && "location", !x.receipt_number && "receipt number"].filter(Boolean);
  if (missing.length) out.push(`Some notice details are missing: ${missing.join(", ")}.`);
  if (c.case_source === "dummy_url") out.push("This record uses an illustrative sample notice. It was not read from any URL you entered.");
  out.push("Fine limits and exception rules come from the prototype's configured dataset, built from published summary guides. They have not been verified against the official Act.");
  out.push("This is an informational assessment, not an authoritative legal determination.");
  return out;
}

export function buildReferences(c: CaseDetail): string[] {
  const refs: string[] = [];
  const a = c.analysis;
  const rule = c.matched_rule;
  if (rule) refs.push(`Road Transport Act, 2018, Section ${rule.section}: ${rule.title} (offence rule and fine limit from the configured dataset)`);
  if (a?.cited_rule_section && a.cited_rule_section !== rule?.section) refs.push(`Section ${a.cited_rule_section} as cited on the notice`);
  for (const e of a?.exceptions ?? []) if (!refs.includes(e.source_reference)) refs.push(e.source_reference);
  return refs;
}
