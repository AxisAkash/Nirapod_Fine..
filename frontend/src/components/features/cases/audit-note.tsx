import Link from "next/link";

import { auditStatusMeta } from "@/lib/audit";
import type { AuditSummary } from "@/types/api";

/** A one-line audit status for the result page. */
export function AuditNote({ caseId, audit }: { caseId: string; audit: AuditSummary }) {
  if (!audit.enabled && audit.status === "not_recorded") return null;
  const meta = auditStatusMeta(audit);
  return (
    <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
      <i className={`size-2 rounded-full ${audit.status === "sealed" ? "bg-ok" : "bg-warn"}`} aria-hidden="true" />
      Audit: {meta.label.toLowerCase()}
      {audit.latest?.block_number != null && ` (block #${audit.latest.block_number})`}.{" "}
      <Link href={`/cases/${caseId}`} className="text-primary hover:underline">
        Verify on the case record
      </Link>
    </p>
  );
}
