"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { TONE_STYLES } from "@/constants/status";
import { auditStatusMeta, canRecord, verifyMeta } from "@/lib/audit";
import { formatDateTime, shortHash } from "@/lib/format";
import { cn } from "@/lib/utils";
import { recordCase, verifyCase } from "@/services/cases.client";
import type { AuditSummary, VerifyResult } from "@/types/api";

const mono = "font-mono text-xs break-all";

/** The blockchain audit record of a case, with a button that checks nothing has changed since it was recorded. */
export function AuditPanel({ caseId, audit }: { caseId: string; audit: AuditSummary }) {
  const router = useRouter();
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [busy, setBusy] = useState<"verify" | "record" | null>(null);
  const meta = auditStatusMeta(audit);
  const latest = audit.latest;

  async function run(kind: "verify" | "record") {
    setBusy(kind);
    try {
      if (kind === "verify") setResult(await verifyCase(caseId));
      else {
        const next = await recordCase(caseId);
        toast[next.status === "sealed" ? "success" : "message"](next.status === "sealed" ? "Recorded on the blockchain." : "Still waiting: the blockchain could not be reached.");
        setResult(null);
        router.refresh();
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(null);
    }
  }

  if (!audit.enabled && audit.status === "not_recorded") {
    return <p className="text-sm text-muted-foreground">Blockchain auditing is switched off on this server, so this case has no audit record.</p>;
  }

  const vm = result ? verifyMeta(result.status) : null;
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("rounded-full px-2.5 py-0.5 font-mono text-xs", TONE_STYLES[meta.tone].soft)}>{meta.label}</span>
        {audit.records > 1 && <span className="text-xs text-muted-foreground">{audit.records} records: the original and later corrections are all kept</span>}
      </div>

      {latest ? (
        <dl className="grid grid-cols-[7.5rem_1fr] gap-x-3 gap-y-1.5 text-sm">
          <dt className="text-muted-foreground">Network</dt>
          <dd>{latest.network ?? "-"}</dd>
          <dt className="text-muted-foreground">Block</dt>
          <dd>{latest.block_number != null ? `#${latest.block_number}` : "-"}</dd>
          <dt className="text-muted-foreground">Transaction</dt>
          <dd className={mono}>{latest.transaction_hash ?? "-"}</dd>
          <dt className="text-muted-foreground">Case hash</dt>
          <dd className={mono}>{latest.case_hash}</dd>
          <dt className="text-muted-foreground">Dataset hash</dt>
          <dd className={mono}>{latest.dataset_hash}</dd>
          <dt className="text-muted-foreground">Result hash</dt>
          <dd className={mono}>{latest.result_hash}</dd>
          {latest.error && (
            <>
              <dt className="text-muted-foreground">Note</dt>
              <dd className="text-warn">{latest.error}</dd>
            </>
          )}
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">This case has not been recorded on the blockchain.</p>
      )}
      <p className="text-xs text-muted-foreground">Only these three hashes go on the blockchain. The receipt, names and case details stay in the database.</p>

      <div className="flex flex-wrap gap-2">
        {latest?.status === "sealed" && (
          <Button onClick={() => run("verify")} disabled={busy !== null}>
            {busy === "verify" ? "Verifying…" : "Verify now"}
          </Button>
        )}
        {canRecord(audit) && (
          <Button variant="outline" onClick={() => run("record")} disabled={busy !== null}>
            {busy === "record" ? "Recording…" : "Record now"}
          </Button>
        )}
      </div>

      {result && vm && (
        <div className="grid gap-3" aria-live="polite">
          <div className={cn("rounded-lg border px-3.5 py-3 text-sm", TONE_STYLES[vm.tone].soft, TONE_STYLES[vm.tone].border)}>
            <b className="block">{vm.label}</b>
            {result.message}
          </div>
          {result.rows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="font-mono text-xs text-muted-foreground uppercase">
                  <tr>
                    <th className="py-1.5 pr-3 font-medium">Item</th>
                    <th className="py-1.5 pr-3 font-medium">Recomputed now</th>
                    <th className="py-1.5 pr-3 font-medium">Recorded</th>
                    <th className="py-1.5 pr-3 font-medium">On the blockchain</th>
                    <th className="py-1.5 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((r) => (
                    <tr key={r.item} className="border-t align-top">
                      <td className="py-2 pr-3 font-medium">{r.item}</td>
                      <td className="py-2 pr-3 font-mono text-xs" title={r.recomputed}>{shortHash(r.recomputed)}</td>
                      <td className="py-2 pr-3 font-mono text-xs" title={r.recorded}>{shortHash(r.recorded)}</td>
                      <td className="py-2 pr-3 font-mono text-xs" title={r.on_chain ?? undefined}>{r.on_chain ? shortHash(r.on_chain) : "-"}</td>
                      <td className="py-2">
                        <span className={cn("rounded-full px-2 py-0.5 font-mono text-[0.68rem]", r.ok ? "bg-ok-bg text-ok" : "bg-bad-bg text-bad")}>{r.ok ? "match" : "mismatch"}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {result.history.length > 1 && (
            <div>
              <p className="mb-1 font-mono text-xs tracking-wider text-muted-foreground uppercase">History</p>
              <ol className="grid gap-1 text-sm">
                {result.history.map((h, i) => (
                  <li key={h.id} className="flex flex-wrap gap-x-3">
                    <span className="font-mono text-xs text-muted-foreground">#{i + 1}</span>
                    <span>{formatDateTime(h.sealed_at ?? h.created_at)}</span>
                    <span className="text-muted-foreground">{h.status}</span>
                    {h.current && <span className="text-primary">latest</span>}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
