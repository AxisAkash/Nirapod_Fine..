import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";

import { ChecksTable, EmptyChecks } from "@/components/features/dashboard/checks-table";
import { StatsRow } from "@/components/features/dashboard/stats-row";
import { UrlCard } from "@/components/features/dashboard/url-card";
import { StatsAndTableSkeleton } from "@/components/layouts/page-skeleton";
import { buttonVariants } from "@/components/ui/button";
import { firstName } from "@/lib/cases";
import { getMe, listCases } from "@/services/data.server";

export const metadata: Metadata = { title: "Overview" };

const headingClass = "mt-0.5 text-[1.6rem] font-semibold";

/** The heading, the URL card and the page frame show at once; the greeting name and the checks stream in. */
export default function DashboardPage() {
  return (
    <>
      <div>
        <p className="font-mono text-[0.72rem] tracking-[0.08em] text-muted-foreground uppercase">Overview</p>
        <Suspense fallback={<h1 className={headingClass}>Welcome back</h1>}>
          <Greeting />
        </Suspense>
        <p className="mt-1 max-w-[60ch] text-muted-foreground">Review traffic fine notices and understand the rules behind each assessment.</p>
      </div>

      <UrlCard />

      <Suspense fallback={<StatsAndTableSkeleton />}>
        <YourChecks />
      </Suspense>
    </>
  );
}

async function Greeting() {
  const name = firstName((await getMe()).full_name);
  return <h1 className={headingClass}>Welcome back{name ? `, ${name}` : ""}</h1>;
}

async function YourChecks() {
  const all = await listCases({ limit: 200 });
  const recent = all.items.slice(0, 5);
  return (
    <>
      <StatsRow cases={all.items} />
      <section aria-labelledby="recent-title">
        <div className="mb-2.5 flex items-center justify-between gap-2">
          <h2 id="recent-title" className="font-sans text-[1.1rem] font-semibold">
            Recent checks
          </h2>
          {all.items.length > 5 && (
            <Link href="/checks" className={buttonVariants({ variant: "outline", size: "sm" })}>
              View all checks
            </Link>
          )}
        </div>
        <div className="overflow-hidden rounded-lg border bg-card">{recent.length ? <ChecksTable cases={recent} /> : <EmptyChecks showAction={false} />}</div>
      </section>
    </>
  );
}
