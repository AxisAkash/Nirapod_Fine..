import type { Metadata } from "next";
import { Suspense } from "react";

import { StatsRow } from "@/components/features/dashboard/stats-row";
import { UrlCard } from "@/components/features/dashboard/url-card";
import { StatsSkeleton } from "@/components/layouts/page-skeleton";
import { firstName } from "@/lib/cases";
import { getMe, listCases } from "@/services/data.server";

export const metadata: Metadata = { title: "Overview" };

const headingClass = "mt-0.5 text-[1.6rem] font-semibold";

/** The heading and the check card show at once; the greeting name and the summary cards stream in. */
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

      <Suspense fallback={<StatsSkeleton />}>
        <YourChecks />
      </Suspense>

      <UrlCard />
    </>
  );
}

async function Greeting() {
  const name = firstName((await getMe()).full_name);
  return <h1 className={headingClass}>Welcome back{name ? `, ${name}` : ""}</h1>;
}

async function YourChecks() {
  const all = await listCases({ limit: 200 });
  return <StatsRow cases={all.items} />;
}
