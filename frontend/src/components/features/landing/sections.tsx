import type { ReactNode } from "react";
import Link from "next/link";

import { amberButton, sizeLg } from "@/components/features/landing/buttons";
import { LandingIcon } from "@/components/features/landing/landing-icon";
import { CAPABILITIES, CHECKS, OUTCOMES, SITUATIONS, STEPS, type Tile } from "@/constants/landing";
import { cn } from "@/lib/utils";

/** A full-width band. `alt` bands are white; the others use the warm background. */
function Band({ id, alt, children }: { id: string; alt?: boolean; children: ReactNode }) {
  return (
    <section id={id} className={cn("scroll-mt-[60px] border-t py-[clamp(56px,8vw,96px)]", alt ? "bg-card" : "bg-warm")}>
      <div className="mx-auto max-w-[1320px] px-[clamp(16px,3vw,32px)]">{children}</div>
    </section>
  );
}

function SectionHead({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="mb-8 grid max-w-[640px] gap-2">
      <div className="font-mono text-[0.72rem] font-medium tracking-[0.08em] text-muted-foreground uppercase">{eyebrow}</div>
      <h2 className="font-sans text-[clamp(1.6rem,3vw,2.15rem)] leading-[1.2] font-semibold tracking-[-0.015em]">{title}</h2>
      {sub && <p className="text-muted-foreground">{sub}</p>}
    </div>
  );
}

function TileCard({ tile, onWarm }: { tile: Tile; onWarm?: boolean }) {
  return (
    <div className={cn("grid min-w-0 content-start gap-2.5 rounded-lg border p-5 transition hover:border-primary hover:shadow-[0_4px_14px_rgba(15,42,32,0.08)]", onWarm ? "bg-warm" : "bg-card")}>
      <div className="grid size-10 place-items-center rounded-lg border bg-card text-primary">
        <LandingIcon name={tile.icon} />
      </div>
      <h3 className="font-sans text-[1.02rem] leading-[1.3] font-semibold">{tile.title}</h3>
      <p className="text-[0.92rem] text-muted-foreground">{tile.text}</p>
    </div>
  );
}

export function Capabilities() {
  return (
    <Band id="overview">
      <SectionHead eyebrow="Capabilities" title="What the prototype does" />
      <div className="grid gap-4 md:grid-cols-3">
        {CAPABILITIES.map((t) => (
          <TileCard key={t.title} tile={t} />
        ))}
      </div>
    </Band>
  );
}

export function Situations() {
  return (
    <Band id="situations" alt>
      <SectionHead eyebrow="Situations" title="Traffic situations, clearly explained." sub="Examples of what a receipt can be checked against." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {SITUATIONS.map((t) => (
          <TileCard key={t.title} tile={t} onWarm />
        ))}
      </div>
      <p className="mt-5 max-w-[70ch] text-sm text-muted-foreground">
        Nirapod Fine does not support every traffic offence. A receipt that does not match the dataset is flagged for manual review.
      </p>
    </Band>
  );
}

export function HowItWorks() {
  return (
    <Band id="how">
      <SectionHead eyebrow="How it works" title="Three steps from receipt to result" />
      <ol className="m-0 grid list-none gap-6 p-0 md:grid-cols-3 md:gap-8">
        {STEPS.map((s) => (
          <li key={s.no} className="min-w-0 border-l-2 pl-5 md:border-l-0 md:pl-0">
            <span className="block font-mono text-[0.8rem] font-medium text-primary">{s.no}</span>
            <div className="relative my-2.5 mb-4 hidden h-px bg-border before:absolute before:-top-1 before:left-0 before:size-[9px] before:rounded-full before:bg-primary before:content-[''] md:block" />
            <h3 className="mb-1.5 font-sans text-[1.1rem] leading-[1.3] font-semibold">{s.title}</h3>
            <p className="max-w-[38ch] text-[0.94rem] text-muted-foreground">{s.text}</p>
          </li>
        ))}
      </ol>
    </Band>
  );
}

export function Checks() {
  return (
    <Band id="checks" alt>
      <SectionHead
        eyebrow="What we check"
        title="Four questions on every receipt"
        sub="The checks are informational and depend on the configured dataset and the details available on the receipt."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CHECKS.map((t) => (
          <TileCard key={t.title} tile={t} onWarm />
        ))}
      </div>
    </Band>
  );
}

const OUTCOME_STYLE = {
  ok: "border-ok bg-ok-bg text-ok",
  warn: "border-warn bg-warn-bg text-warn",
  neutral: "border-border bg-muted text-foreground",
} as const;

export function Outcomes() {
  return (
    <Band id="results">
      <SectionHead eyebrow="Possible results" title="Three outcomes, each with a clear label" sub="Shown for illustration. Each state is named in text as well as colour." />
      <div className="grid gap-4 md:grid-cols-3">
        {OUTCOMES.map((o) => (
          <div key={o.label} className={cn("grid min-w-0 content-start gap-2 rounded-lg border p-[18px]", OUTCOME_STYLE[o.tone])}>
            <div className="flex items-center gap-2.5 text-[1.02rem] font-semibold">
              <LandingIcon name={o.icon} className="size-[22px] shrink-0" />
              <span>{o.label}</span>
            </div>
            <p className="text-[0.92rem] text-muted-foreground">{o.text}</p>
          </div>
        ))}
      </div>
    </Band>
  );
}

export function CtaBand() {
  return (
    <section className="bg-navy py-[clamp(48px,7vw,80px)] text-white">
      <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-x-10 gap-y-5 px-[clamp(16px,3vw,32px)]">
        <div>
          <h2 className="max-w-[24ch] font-sans text-[clamp(1.5rem,3vw,2.1rem)] leading-[1.2] font-semibold tracking-[-0.015em] text-white">
            Understand your traffic fine before drawing conclusions.
          </h2>
          <p className="mt-2 max-w-[52ch] text-[#b9cfc3]">Review the recorded details, applicable rules, and available evidence in one place.</p>
        </div>
        <Link href="/upload" className={cn(amberButton, sizeLg)}>
          Check Mamla
        </Link>
      </div>
    </section>
  );
}
