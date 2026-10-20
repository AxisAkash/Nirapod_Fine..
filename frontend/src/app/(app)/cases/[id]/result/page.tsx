import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AmountCheck } from "@/components/features/cases/amount-check";
import { AuditNote } from "@/components/features/cases/audit-note";
import { AnalyzeNow } from "@/components/features/cases/analyze-now";
import { ExplanationBody } from "@/components/features/cases/explanation-card";
import { ExtractedFields } from "@/components/features/cases/extracted-fields";
import { JustificationList } from "@/components/features/cases/justification-list";
import { MatchedSection } from "@/components/features/cases/matched-section";
import { SectionCard } from "@/components/features/cases/section-card";
import { VerdictBanner } from "@/components/features/cases/verdict-banner";
import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { buttonVariants } from "@/components/ui/button";
import { NeutralPill } from "@/components/ui/result-pill";
import { cn } from "@/lib/utils";
import { buildLimitations, buildReferences } from "@/lib/cases";
import { getCase } from "@/services/data.server";

export const metadata: Metadata = { title: "Result" };

const amber = "inline-flex items-center rounded-md border border-lamp bg-lamp px-4 py-2 text-sm font-semibold text-[#0f2a20] hover:brightness-105";

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

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Link href="/dashboard" className={buttonVariants({ variant: "outline", size: "sm" })}>
          &larr; Overview
        </Link>
        <Link href="/checks" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Recent checks
        </Link>
        {sample && <NeutralPill>Illustrative sample</NeutralPill>}
      </div>

      {sample && (
        <div className="rounded-r-md border-l-[3px] border-warn bg-warn-bg px-3.5 py-2.5 text-[0.88rem]">
          This result comes from an illustrative sample notice. It was not produced from a URL or document you provided.
        </div>
      )}

      <VerdictBanner status={c.validation_status} summary={c.validation_summary} flags={a.flags} />

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title={`Notice information${sample ? " (illustrative sample)" : ""}`}>
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
        <SectionCard title="Identified offence and legal section">
          <MatchedSection analysis={a} confidenceLabel="Match confidence" />
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Configured fine limit">
          <AmountCheck amount={c.extracted.amount} analysis={a} />
        </SectionCard>
        <SectionCard title="Relevant exception checks">
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
        </SectionCard>
      </div>

      <SectionCard title="Checks performed">
        <JustificationList items={checks} />
      </SectionCard>

      <SectionCard title="Explanation">
        <ExplanationBody text={c.ai_explanation} analysis={a} />
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Supporting legal references">
          {references.length ? (
            <ul className="grid list-disc gap-1.5 pl-5 text-sm">
              {references.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No section was matched, so there are no references to show.</p>
          )}
          <p className="mt-2.5 text-xs text-muted-foreground">Summaries come from the prototype dataset. Check them against the official Act.</p>
        </SectionCard>
        <SectionCard title="Missing information and limitations">
          <ul className="grid list-disc gap-1.5 pl-5 text-sm">
            {limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/cases/${c.id}`} className={buttonVariants({ size: "lg" })}>
          View full case record
        </Link>
        <Link href="/dashboard#notice" className={amber}>
          Analyze another mamla
        </Link>
      </div>
      <AuditNote caseId={c.id} audit={c.audit} />
      <p className="border-t pt-3.5 text-[0.82rem] text-muted-foreground">Informational tool, not legal advice. Dataset: {a.dataset}.</p>
    </>
  );
}
