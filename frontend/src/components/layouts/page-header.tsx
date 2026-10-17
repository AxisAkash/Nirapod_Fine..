import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, actions }: { eyebrow?: string; title: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
      <div className="min-w-0">
        {eyebrow && <p className="font-mono text-xs tracking-wider text-muted-foreground uppercase">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold sm:text-3xl">{title}</h1>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
