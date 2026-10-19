import type { Tone } from "@/constants/status";
import type { AuditSummary, DatasetIntegrity, VerifyResult } from "@/types/api";

export interface Meta {
  label: string;
  tone: Tone;
}

export function auditStatusMeta(audit: AuditSummary): Meta {
  if (!audit.enabled && audit.status === "not_recorded") return { label: "Auditing off", tone: "neutral" };
  switch (audit.status) {
    case "sealed":
      return { label: "Recorded on blockchain", tone: "ok" };
    case "pending":
      return { label: "Waiting to be recorded", tone: "warn" };
    case "failed":
      return { label: "Could not be recorded", tone: "bad" };
    default:
      return { label: "Not recorded", tone: "neutral" };
  }
}

export function verifyMeta(status: VerifyResult["status"]): Meta {
  switch (status) {
    case "verified":
      return { label: "Verified: unchanged", tone: "ok" };
    case "mismatch":
      return { label: "Verification failed", tone: "bad" };
    case "not_on_chain":
      return { label: "Not found on the blockchain", tone: "warn" };
    case "unavailable":
      return { label: "Blockchain unreachable", tone: "neutral" };
    case "pending":
      return { label: "Waiting to be recorded", tone: "warn" };
    case "failed":
      return { label: "Could not be recorded", tone: "bad" };
    default:
      return { label: "Not recorded", tone: "neutral" };
  }
}

export function integrityMeta(status: DatasetIntegrity["status"]): Meta {
  switch (status) {
    case "verified":
      return { label: "Verified", tone: "ok" };
    case "tampered":
      return { label: "Does not match", tone: "bad" };
    case "unanchored":
      return { label: "Not recorded yet", tone: "warn" };
    case "unchecked":
      return { label: "Could not be checked", tone: "neutral" };
    default:
      return { label: "Auditing off", tone: "neutral" };
  }
}

/** Whether a "Record now" action makes sense for this audit state. */
export function canRecord(audit: AuditSummary): boolean {
  return audit.enabled && (audit.status === "pending" || audit.status === "failed" || audit.status === "not_recorded");
}
