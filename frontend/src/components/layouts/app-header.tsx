"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";

import { Logo } from "@/components/layouts/logo";
import { APP_NAV } from "@/constants/nav";
import { cn } from "@/lib/utils";

const linkClass = "border-b-2 border-transparent px-0.5 py-1.5 text-[0.88rem] font-medium whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground";

/** Highlights the current section. Reading the path happens at request time, so this part streams in. */
function NavLinks({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();
  // A case's page is the Result tab; the old upload page belongs to Overview.
  const section = pathname.startsWith("/cases") ? "/result" : pathname.startsWith("/upload") ? "/dashboard" : pathname;
  return (
    <>
      {APP_NAV.filter((n) => !n.adminOnly || isAdmin).map((n) => {
        const current = section === n.href || section.startsWith(`${n.href}/`);
        return (
          <Link key={n.href} href={n.href} aria-current={current ? "page" : undefined} className={cn(linkClass, current && "border-primary text-primary hover:text-primary")}>
            {n.label}
          </Link>
        );
      })}
    </>
  );
}

function PlainLinks({ isAdmin }: { isAdmin: boolean }) {
  return (
    <>
      {APP_NAV.filter((n) => !n.adminOnly || isAdmin).map((n) => (
        <Link key={n.href} href={n.href} className={linkClass}>
          {n.label}
        </Link>
      ))}
    </>
  );
}

export function AppHeader({ isAdmin }: { isAdmin: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b bg-card">
      <div className="mx-auto flex max-w-(--page-max) flex-wrap items-center gap-x-[22px] gap-y-1 px-[clamp(16px,3vw,32px)] py-2.5">
        <Logo href="/dashboard" />
        <nav aria-label="Main" className="order-3 flex w-full gap-x-[22px] overflow-x-auto sm:order-none sm:ml-1 sm:w-auto">
          <Suspense fallback={<PlainLinks isAdmin={isAdmin} />}>
            <NavLinks isAdmin={isAdmin} />
          </Suspense>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {isAdmin && <span className="hidden rounded-full bg-accent px-2 py-0.5 font-mono text-[0.7rem] text-accent-foreground sm:inline">admin</span>}
          <UserButton />
        </div>
      </div>
    </header>
  );
}
