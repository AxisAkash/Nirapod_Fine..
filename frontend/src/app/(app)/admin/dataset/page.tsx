import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminTabs } from "@/components/features/admin/admin-tabs";
import { ExceptionsPanel } from "@/components/features/admin/exceptions-panel";
import { RulesPanel } from "@/components/features/admin/rules-panel";
import { VersionsPanel } from "@/components/features/admin/versions-panel";
import { PageHeader } from "@/components/layouts/page-header";
import { PageSkeleton } from "@/components/layouts/page-skeleton";
import { getAdminExceptions, getAdminRules, getAdminVersions, getMe } from "@/services/data.server";

export const metadata: Metadata = { title: "Admin dataset" };

export default function AdminDatasetPage({ searchParams }: PageProps<"/admin/dataset">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <AdminContent searchParams={searchParams} />
    </Suspense>
  );
}

async function AdminContent({ searchParams }: { searchParams: PageProps<"/admin/dataset">["searchParams"] }) {
  const me = await getMe();
  if (me.role !== "admin") {
    return (
      <div role="alert" className="mx-auto max-w-lg rounded-xl border bg-card p-6 text-center">
        <h2 className="text-lg font-semibold">Admin access only</h2>
        <p className="mt-2 text-sm text-muted-foreground">Your account does not have the admin role. Ask an administrator to grant it.</p>
      </div>
    );
  }

  const sp = await searchParams;
  const tab = typeof sp.tab === "string" ? sp.tab : "versions";
  const versions = await getAdminVersions();
  const wanted = typeof sp.version === "string" ? sp.version : undefined;
  const version = versions.find((v) => v.id === wanted) ?? versions.find((v) => v.is_active) ?? versions[0];

  return (
    <>
      <PageHeader eyebrow="Admin" title="Legal dataset" />
      {version ? (
        <>
          <AdminTabs current={tab} versionId={version.id} />
          {tab === "rules" && <RulesPanel version={version} rules={await getAdminRules(version.id)} />}
          {tab === "exceptions" && <ExceptionsPanel version={version} rules={await getAdminExceptions(version.id)} />}
          {tab !== "rules" && tab !== "exceptions" && <VersionsPanel versions={versions} />}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">No dataset version exists yet. Run the seed command on the backend.</p>
      )}
    </>
  );
}
