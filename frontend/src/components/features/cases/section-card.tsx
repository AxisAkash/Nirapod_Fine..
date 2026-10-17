import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A white card with a small uppercase label, the building block of the result and case pages. */
export function SectionCard({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("min-w-0 rounded-xl border bg-card p-4", className)}>
      <h3 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">{title}</h3>
      {children}
    </section>
  );
}
