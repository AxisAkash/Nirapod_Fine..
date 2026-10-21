import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AmountCheck } from "@/components/features/cases/amount-check";
import { Disclosure } from "@/components/features/cases/disclosure";
import { AuditPanel } from "@/components/features/cases/audit-panel";
import { AnalyzeNow } from "@/components/features/cases/analyze-now";
import { ExplanationBody } from "@/components/features/cases/explanation-card";
import { ExtractedFields } from "@/components/features/cases/extracted-fields";
import { JustificationList } from "@/components/features/cases/justification-list";
import { KeyFacts } from "@/components/features/cases/key-facts";
import { ReceiptPreview } from "@/components/features/cases/receipt-preview";
import { MatchedSection } from "@/components/features/cases/matched-section";
import { SectionCard } from "@/components/features/cases/section-card";
import { VerdictBanner } from "@/components/features/cases/verdict-banner";
import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { buttonVariants } from "@/components/ui/button";
import { NeutralPill } from "@/components/ui/result-pill";
import { cn } from "@/lib/utils";
import { auditStatusMeta } from "@/lib/audit";
import { buildLimitations, buildReferences } from "@/lib/cases";
import { getCase } from "@/services/data.server";

export const metadata: Metadata = { title: "Result" };

export default function ResultPage({ params }: PageProps<"/cases/[id]/result">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ResultContent params={params} />
    </Suspense>
  );
}

async function ResultContent({ params }: { params: PageProps<"/cases/[id]/result">["params"] }) {
  const { id } = await params;
  const c = await getCase(id);
  if (!c) notFound();

  if (!c.analysis) {
    return (
      <>
        <PageHeader eyebrow="Case" title="This case has not been analysed yet" />
        <div className="rounded-lg border bg-card p-6">
          <p className="mb-4 text-sm text-muted-foreground">The notice was saved. Run the analysis to see the result.</p>
          <div className="flex flex-wrap gap-2">
            <AnalyzeNow caseId={c.id} />
          </div>
        </div>
      </>
    );
  }

  const a = c.analysis;
  const sample = c.case_source === "dummy_url";
  const references = buildReferences(c);
  const limitations = buildLimitations(c);
  const checks = a.justifications.filter((j) => j.kind !== "exception");

  const mayApply = a.exceptions.filter((e) => e.applies).length;

  const when = new Date(c.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const source = c.receipt?.file_name ?? (sample ? "Illustrative sample" : "Mamla");

  return (
    <>
      <PageHeader
        eyebrow="Result"
        title="Fine check result"
        actions={
          <Link href="/dashboard#notice" className={buttonVariants({ variant: "outline" })}>
            Check another mamla
          </Link>
        }
      />
      <p className="-mt-3 truncate text-sm text-muted-foreground">
        {source} &middot; checked {when}
      </p>

      {sample && (
        <div className="rounded-r-md border-l-[3px] border-warn bg-warn-bg px-3.5 py-2.5 text-[0.88rem]">
          <NeutralPill>Illustrative sample</NeutralPill> This result comes from an illustrative sample notice. It was not produced from a URL or document you provided.
        </div>
      )}

      <VerdictBanner status={c.validation_status} summary={c.validation_summary} flags={a.flags} />

      <KeyFacts amount={c.extracted.amount} analysis={a} />

      <SectionCard title="Explanation">
        <ExplanationBody text={c.ai_explanation} analysis={a} />
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title={`Receipt details${sample ? " (illustrative sample)" : ""}`}>
          <ExtractedFields data={c.extracted} />
          {c.dummy_url && (
            <dl className="mt-1.5 grid grid-cols-[8rem_1fr] gap-x-3 text-sm">
              <dt className="text-muted-foreground">URL entered</dt>
              <dd className="font-mono text-xs break-all text-muted-foreground">
                {c.dummy_url}
                <br />
                Not fetched
              </dd>
            </dl>
          )}
        </SectionCard>
        <SectionCard title="Fine limit">
          <AmountCheck amount={c.extracted.amount} analysis={a} />
        </SectionCard>
      </div>

      <section aria-label="Supporting detail" className="grid gap-3">
        <h2 className="font-sans text-[1.05rem] font-semibold">Supporting detail</h2>
        <Disclosure
          title="Exception checks"
          hint="Whether an emergency, permit or special-vehicle rule could change the outcome"
          defaultOpen={mayApply > 0}
          badge={mayApply > 0 ? <span className="rounded-full bg-warn-bg px-2.5 py-0.5 font-mono text-xs text-warn">{mayApply} may apply</span> : undefined}
        >
          {a.exceptions.length ? (
            <ul className="grid gap-2">
              {a.exceptions.map((e) => (
                <li key={e.key} className="grid gap-1 rounded-lg border p-3 text-sm">
                  <p>
                    <b className="font-medium">{e.title}</b>{" "}
                    <span className={cn("rounded-full px-2.5 py-0.5 font-mono text-xs", e.applies ? "bg-warn-bg text-warn" : "bg-muted text-muted-foreground")}>
                      {e.applies ? "may apply" : "does not apply"}
                    </span>
                  </p>
                  <p className="text-muted-foreground">{e.reason}</p>
                  <p className="font-mono text-xs text-muted-foreground">{e.source_reference}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No exception rule was triggered.
              {c.matched_rule && " No emergency, permit or special-vehicle claim was found, and the vehicle type matched none of the configured exceptions."}
            </p>
          )}
        </Disclosure>
        <Disclosure title="How the section was matched" hint="The offence match, its confidence and the checks that were run">
          <div className="grid gap-5">
            <MatchedSection analysis={a} confidenceLabel="Match confidence" />
            <div>
              <h3 className="mb-2 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Checks performed</h3>
              <JustificationList items={checks} />
            </div>
          </div>
        </Disclosure>
        <Disclosure title="Legal references" hint="Summaries from the prototype dataset. Check them against the official Act.">
          {references.length ? (
            <ul className="grid list-disc gap-1.5 pl-5 text-sm">
              {references.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No section was matched, so there are no references to show.</p>
          )}
        </Disclosure>
        <Disclosure title="Missing information and limitations">
          <ul className="grid list-disc gap-1.5 pl-5 text-sm">
            {limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </Disclosure>
        <Disclosure title={sample ? "Illustrative sample notice" : "Original receipt"} hint="The receipt and all the details taken from it">
          <div className="grid items-start gap-6 lg:grid-cols-2">
            <ReceiptPreview receipt={c.receipt} extracted={c.extracted} />
            <div className="grid min-w-0 gap-5">
              <ExtractedFields data={c.extracted} />
              {c.receipt?.text_read && (
                <div>
                  <h3 className="mb-2 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Text read from the receipt</h3>
                  <pre className="max-h-72 overflow-auto rounded-lg border bg-muted p-3 font-sans text-[0.82rem] whitespace-pre-wrap">{c.receipt.text_read}</pre>
                </div>
              )}
            </div>
          </div>
        </Disclosure>
        {(c.audit.enabled || c.audit.status !== "not_recorded") && (
          <Disclosure
            title="Blockchain audit record"
            hint="Proof that this result has not been changed since it was recorded"
            badge={<span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-xs text-muted-foreground">{auditStatusMeta(c.audit).label}</span>}
          >
            <AuditPanel caseId={c.id} audit={c.audit} />
          </Disclosure>
        )}
      </section>

      <p className="border-t pt-3.5 text-[0.82rem] text-muted-foreground">Informational tool, not legal advice. Dataset: {a.dataset}.</p>
    </>
  );
}
