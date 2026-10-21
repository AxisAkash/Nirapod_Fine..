import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { buttonVariants } from "@/components/ui/button";
import { listCases } from "@/services/data.server";

export const metadata: Metadata = { title: "Result" };

export default function ResultIndexPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <LatestResult />
    </Suspense>
  );
}

/** The Result tab opens your most recent result. Older ones are opened from Recent Checks. */
async function LatestResult() {
  const latest = (await listCases({ limit: 1 })).items[0];
  if (latest) redirect(`/cases/${latest.id}/result`);
  return (
    <>
      <PageHeader eyebrow="Result" title="No results yet" />
      <div className="rounded-xl border bg-card px-6 py-10 text-center">
        <p className="mx-auto max-w-[46ch] text-muted-foreground">Your results appear here once you have analysed a mamla. Start from the Overview page.</p>
        <Link href="/dashboard#notice" className={buttonVariants({ size: "lg" }) + " mt-4"}>
          Check a mamla
        </Link>
      </div>
    </>
  );
}
