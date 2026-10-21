import type { ValidationStatus } from "@/types/api";

export type Tone = "ok" | "bad" | "warn" | "rev" | "neutral";

export interface StatusMeta {
  label: string;
  headline: string;
  tone: Tone;
}

export const STATUS_META: Record<ValidationStatus, StatusMeta> = {
  VALID: { label: "Valid", headline: "Fine is valid", tone: "ok" },
  INVALID_FINE_TOO_HIGH: { label: "Fine too high", headline: "Fine too high", tone: "bad" },
  INVALID_REASON_MISMATCH: {
    label: "Reason mismatch",
    headline: "Reason does not match the section",
    tone: "bad",
  },
  VALID_BUT_EXCEPTION_POSSIBLE: {
    label: "Exception possible",
    headline: "Valid, but an exception may apply",
    tone: "warn",
  },
  INVALID_EXCEPTION_NOT_APPLICABLE: {
    label: "Exception not applicable",
    headline: "Claimed exception does not apply",
    tone: "bad",
  },
  NEEDS_MANUAL_REVIEW: { label: "Needs manual review", headline: "Needs manual review", tone: "rev" },
  PENDING_ANALYSIS: { label: "Not analysed yet", headline: "Not analysed yet", tone: "rev" },
};

/** Statuses a finished analysis can produce, in the order shown to users. */
export const RESULT_STATUSES: ValidationStatus[] = [
  "VALID",
  "INVALID_FINE_TOO_HIGH",
  "INVALID_REASON_MISMATCH",
  "VALID_BUT_EXCEPTION_POSSIBLE",
  "INVALID_EXCEPTION_NOT_APPLICABLE",
  "NEEDS_MANUAL_REVIEW",
];

/** Tailwind classes for each tone: soft background with a strong foreground. */
export const TONE_STYLES: Record<Tone, { soft: string; border: string; stripe: string; solid: string }> = {
  neutral: { soft: "bg-muted text-muted-foreground", border: "border-border", stripe: "border-border", solid: "bg-muted-foreground" },
  ok: { soft: "bg-ok-bg text-ok", border: "border-ok", stripe: "border-ok", solid: "bg-ok" },
  bad: { soft: "bg-bad-bg text-bad", border: "border-bad", stripe: "border-bad", solid: "bg-bad" },
  warn: { soft: "bg-warn-bg text-warn", border: "border-warn", stripe: "border-warn", solid: "bg-warn" },
  rev: { soft: "bg-rev-bg text-rev", border: "border-rev", stripe: "border-rev", solid: "bg-rev" },
};

export const JUSTIFICATION_STRIPE: Record<string, string> = {
  ok: "border-ok",
  bad: "border-bad",
  warn: "border-warn",
  info: "border-primary",
};

/** The three result groups shown on the dashboard and in history. */
export type ResultGroup = "consistent" | "review" | "insufficient";

export const RESULT_GROUPS: Record<ResultGroup, { label: string; tone: Tone }> = {
  consistent: { label: "Consistent", tone: "ok" },
  review: { label: "Review Required", tone: "warn" },
  insufficient: { label: "Insufficient Information", tone: "neutral" },
};

export function groupOf(status: ValidationStatus): ResultGroup {
  if (status === "VALID") return "consistent";
  if (status === "NEEDS_MANUAL_REVIEW" || status === "PENDING_ANALYSIS") return "insufficient";
  return "review";
}
