import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AuditPanel } from "@/components/features/cases/audit-panel";
import { ExplanationBody } from "@/components/features/cases/explanation-card";
import { ExtractedFields } from "@/components/features/cases/extracted-fields";
import { ReceiptPreview } from "@/components/features/cases/receipt-preview";
import { SectionCard } from "@/components/features/cases/section-card";
import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { buttonVariants } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { CASE_SOURCE_LABEL } from "@/constants/status";
import { formatDateTime, formatTaka } from "@/lib/format";
import { cn } from "@/lib/utils";
import { getCase } from "@/services/data.server";

export const metadata: Metadata = { title: "Case record" };

export default function CaseRecordPage({ params }: PageProps<"/cases/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CaseRecordContent params={params} />
    </Suspense>
  );
}

async function CaseRecordContent({ params }: { params: PageProps<"/cases/[id]">["params"] }) {
  const { id } = await params;
  const c = await getCase(id);
  if (!c) notFound();
  const rule = c.matched_rule;
  const a = c.analysis;

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Link href="/dashboard" className={buttonVariants({ variant: "outline", size: "sm" })}>
          &larr; Overview
        </Link>
        <Link href={`/cases/${c.id}/result`} className={buttonVariants({ variant: "outline", size: "sm" })}>
          &larr; Result page
        </Link>
      </div>
      <PageHeader
        eyebrow={`Case record · ${c.id.slice(0, 8)}`}
        title={rule ? `Section ${rule.section} · ${c.extracted.reason ?? ""}` : (c.extracted.reason ?? "Case record")}
        actions={<StatusBadge status={c.validation_status} className="text-sm" />}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title={c.case_source === "dummy_url" ? "Illustrative sample notice" : "Original receipt"}>
          <ReceiptPreview receipt={c.receipt} extracted={c.extracted} />
          <dl className="mt-3 grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Source</dt>
            <dd>
              {c.case_source === "dummy_url" ? "Illustrative sample notice" : (CASE_SOURCE_LABEL[c.case_source] ?? c.case_source)}
              {c.dummy_url && (
                <span className="block text-xs text-muted-foreground">
                  URL entered, not fetched:
                  <span className="block font-mono break-all">{c.dummy_url}</span>
                </span>
              )}
            </dd>
          </dl>
        </SectionCard>

        <div className="grid content-start gap-4">
          <SectionCard title="Structured data">
            <ExtractedFields data={c.extracted} />
          </SectionCard>
          <SectionCard title="Rule match">
            <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1.5 text-sm">
              <dt className="text-muted-foreground">Section</dt>
              <dd>{rule ? `${rule.section}: ${rule.title}` : "none"}</dd>
              <dt className="text-muted-foreground">Max fine</dt>
              <dd>{rule?.max_fine != null ? formatTaka(rule.max_fine) : "-"}</dd>
              <dt className="text-muted-foreground">Allowed</dt>
              <dd>{formatTaka(a?.allowed_fine)}</dd>
              <dt className="text-muted-foreground">Charged</dt>
              <dd>{formatTaka(c.extracted.amount)}</dd>
              <dt className="text-muted-foreground">Repeat</dt>
              <dd>{a?.previous_fine != null ? `Occurrence ${a.occurrence}, previous ${formatTaka(a.previous_fine)}` : "First recorded"}</dd>
              <dt className="text-muted-foreground">Confidence</dt>
              <dd>{c.confidence_score != null ? `${c.confidence_score}%` : "-"}</dd>
              <dt className="text-muted-foreground">Dataset</dt>
              <dd>{c.dataset?.name ?? "-"}</dd>
              <dt className="text-muted-foreground">Checked</dt>
              <dd>{formatDateTime(c.created_at)}</dd>
            </dl>
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Candidate sections">
        {c.matches.length ? (
          <ul className="grid gap-1.5 text-sm">
            {c.matches.map((m) => (
              <li key={m.section} className="flex flex-wrap items-baseline gap-x-3">
                <span className="w-14 font-mono">{m.section}</span>
                <span className="min-w-0 flex-1">{m.title}</span>
                <span className="font-mono text-xs text-muted-foreground tabular-nums">score {m.score}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No candidate sections were scored.</p>
        )}
      </SectionCard>

      <SectionCard title="Exception checks">
        {c.exception_checks.length ? (
          <ul className="grid gap-2">
            {c.exception_checks.map((e) => (
              <li key={e.key} className="grid gap-0.5 rounded-lg border p-3 text-sm">
                <p>
                  <b className="font-medium">{e.title}</b>{" "}
                  <span className={cn("rounded-full px-2 py-0.5 font-mono text-[0.68rem]", e.applies ? "bg-warn-bg text-warn" : "bg-muted text-muted-foreground")}>
                    {e.applies ? "applies" : "does not apply"}
                  </span>
                </p>
                {e.reason && <p className="text-muted-foreground">{e.reason}</p>}
                {e.source_reference && <p className="font-mono text-xs text-muted-foreground">{e.source_reference}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No exception rule was triggered by this case.</p>
        )}
      </SectionCard>

      <SectionCard title="Explanation">
        <ExplanationBody text={c.ai_explanation} analysis={a} />
      </SectionCard>

      <SectionCard title="Blockchain audit record">
        <AuditPanel caseId={c.id} audit={c.audit} />
      </SectionCard>
    </>
  );
}
