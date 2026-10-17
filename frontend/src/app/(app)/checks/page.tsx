import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";

import { ChecksTable, EmptyChecks } from "@/components/features/dashboard/checks-table";
import { ResultFilter } from "@/components/features/dashboard/result-filter";
import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { RESULT_GROUPS, groupOf, type ResultGroup } from "@/constants/status";
import { listCases } from "@/services/data.server";

export const metadata: Metadata = { title: "Recent checks" };

export default function ChecksPage({ searchParams }: PageProps<"/checks">) {
  return (
    <>
      <PageHeader
        eyebrow="History"
        title="Recent checks"
        actions={
          <Link href="/dashboard#notice" className="inline-flex items-center rounded-md border border-lamp bg-lamp px-4 py-2 text-sm font-semibold text-[#1a1305] hover:brightness-105">
            Analyze a notice
          </Link>
        }
      />
      <Suspense fallback={<PageSkeleton />}>
        <ChecksContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function ChecksContent({ searchParams }: { searchParams: PageProps<"/checks">["searchParams"] }) {
  const { result } = await searchParams;
  const filter = typeof result === "string" && result in RESULT_GROUPS ? (result as ResultGroup) : null;
  const all = await listCases({ limit: 200 });
  const shown = filter ? all.items.filter((c) => groupOf(c.validation_status) === filter) : all.items;

  return (
    <>
      <div className="overflow-hidden rounded-lg border bg-card">
        {all.items.length ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 px-3.5 py-3">
              <ResultFilter />
              <span className="text-[0.82rem] text-muted-foreground">
                {shown.length} of {all.items.length} shown
              </span>
            </div>
            {shown.length ? <ChecksTable cases={shown} /> : <div className="px-4 py-9 text-center text-muted-foreground">No checks match this filter.</div>}
          </>
        ) : (
          <EmptyChecks />
        )}
      </div>
      {all.total > all.items.length && <p className="text-xs text-muted-foreground">Showing your {all.items.length} most recent checks.</p>}
    </>
  );
}
