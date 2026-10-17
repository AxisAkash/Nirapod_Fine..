import { Suspense, type ReactNode } from "react";

import { ServiceError } from "@/components/features/cases/service-error";
import { AppHeader } from "@/components/layouts/app-header";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/services/api-error";
import { getMe } from "@/services/data.server";
import type { Me } from "@/types/api";

/** Everything behind sign-in depends on the visitor, so the whole shell streams in behind a skeleton. */
export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<ShellSkeleton />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}

async function AppShell({ children }: { children: ReactNode }) {
  let me: Me;
  try {
    me = await getMe();
  } catch (e) {
    const message = e instanceof ApiError ? e.message : "Something went wrong.";
    return (
      <>
        <AppHeader isAdmin={false} />
        <main className="mx-auto w-full max-w-[1320px] flex-1 px-[clamp(16px,3vw,32px)] py-8">
          <ServiceError message={message} />
        </main>
      </>
    );
  }
  return (
    <>
      <AppHeader isAdmin={me.role === "admin"} />
      <main className="mx-auto flex w-full max-w-[1320px] flex-1 flex-col gap-6 px-[clamp(16px,3vw,32px)] py-6">{children}</main>
    </>
  );
}

function ShellSkeleton() {
  return (
    <>
      <AppHeader isAdmin={false} />
      <main aria-busy="true" aria-label="Loading" className="mx-auto grid w-full max-w-[1320px] flex-1 content-start gap-4 px-[clamp(16px,3vw,32px)] py-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40" />
        <Skeleton className="h-72" />
      </main>
    </>
  );
}
