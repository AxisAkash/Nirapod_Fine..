"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ghostButton, amberButton, sizeSm } from "@/components/features/landing/buttons";
import { LandingIcon } from "@/components/features/landing/landing-icon";
import { SITE } from "@/config/site";
import { LANDING_NAV } from "@/constants/nav";
import { cn } from "@/lib/utils";

function scrollToSection(id: string) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

export function MarketingHeaderView({ signedIn }: { signedIn: boolean }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const go = (id: string) => {
    setOpen(false);
    scrollToSection(id);
  };

  return (
    <header className="sticky top-0 z-30 border-b bg-card">
      <div className="mx-auto flex max-w-(--page-max) items-center gap-x-4 px-[clamp(16px,3vw,32px)] py-2.5">
        <Link href="/" className="font-heading text-[1.1rem] font-semibold text-primary">
          {SITE.name}
        </Link>
        <nav aria-label="Primary" className="ml-5 hidden gap-x-[22px] md:flex">
          {LANDING_NAV.map((l) => (
            <button key={l.id} type="button" onClick={() => go(l.id)} className="py-2 text-[0.88rem] font-medium text-muted-foreground hover:text-foreground">
              {l.label}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2.5">
          {signedIn ? (
            <Link href="/dashboard" className={cn(amberButton, sizeSm, "hidden md:inline-flex")}>
              Dashboard
            </Link>
          ) : (
            <>
              <Link href="/sign-in" className={cn(ghostButton, sizeSm, "hidden md:inline-flex")}>
                Sign in
              </Link>
              <Link href="/dashboard#notice" className={cn(amberButton, sizeSm, "hidden md:inline-flex")}>
                Check Mamla
              </Link>
            </>
          )}
          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((o) => !o)}
            className="grid size-9 place-items-center rounded-lg border bg-card md:hidden"
          >
            <LandingIcon name={open ? "close" : "menu"} className="size-5" />
          </button>
        </div>
      </div>
      <div id="mobile-nav" hidden={!open} className="grid gap-1 border-t bg-card px-[clamp(16px,3vw,32px)] pt-3 pb-4 md:hidden">
        {LANDING_NAV.map((l) => (
          <button key={l.id} type="button" onClick={() => go(l.id)} className="border-b py-3 text-left text-base font-medium text-muted-foreground">
            {l.label}
          </button>
        ))}
        <div className="mt-3 flex gap-2">
          {signedIn ? (
            <Link href="/dashboard" className={cn(amberButton, "flex-1 px-4 py-2.5 text-sm")}>
              Dashboard
            </Link>
          ) : (
            <>
              <Link href="/sign-in" className={cn(ghostButton, "flex-1 px-4 py-2.5 text-sm")}>
                Sign in
              </Link>
              <Link href="/dashboard#notice" className={cn(amberButton, "flex-1 px-4 py-2.5 text-sm")}>
                Check Mamla
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
