"use client";

import Link from "next/link";

import { DISCLAIMER, FOOTER_LINKS } from "@/constants/landing";
import { SITE } from "@/config/site";

function scrollTo(id: string) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

export function SiteFooter() {
  return (
    <footer className="border-t bg-warm py-10">
      <div className="mx-auto max-w-(--page-max) px-[clamp(16px,3vw,32px)]">
        <div className="flex flex-wrap justify-between gap-x-12 gap-y-6">
          <div className="min-w-0 max-w-[44ch]">
            <b className="mb-1.5 block font-heading text-[1.05rem] font-semibold text-primary">{SITE.name}</b>
            <p className="text-sm text-muted-foreground">
              A research prototype that explores how Bangladesh traffic fine receipts can be checked against the Road Transport Act, 2018.
            </p>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap content-start gap-x-6 gap-y-1">
            {FOOTER_LINKS.map((l) => (
              <button key={l.id} type="button" onClick={() => scrollTo(l.id)} className="py-1 text-sm text-muted-foreground hover:text-primary">
                {l.label}
              </button>
            ))}
            <Link href="/dashboard#notice" className="py-1 text-sm text-muted-foreground hover:text-primary">
              Check Mamla
            </Link>
          </nav>
        </div>
        <div role="note" className="mt-7 rounded-lg border bg-card px-4 py-3.5 text-[0.86rem]">
          <b className="mb-1 block font-mono text-[0.7rem] font-medium tracking-[0.07em] text-muted-foreground uppercase">Disclaimer</b>
          {DISCLAIMER}
        </div>
      </div>
    </footer>
  );
}
