import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

/** A collapsible card for supporting detail, so the page leads with the answer and keeps the evidence one click away. */
export function Disclosure({ title, hint, badge, defaultOpen, children }: { title: string; hint?: string; badge?: ReactNode; defaultOpen?: boolean; children: ReactNode }) {
  return (
    <details open={defaultOpen} className="group min-w-0 rounded-xl border bg-card">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3.5 select-none [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">
          <span className="text-[0.95rem] font-semibold">{title}</span>
          {hint && <span className="mt-0.5 block text-xs text-muted-foreground">{hint}</span>}
        </span>
        {badge}
        <ChevronDown aria-hidden="true" className={cn("size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180")} />
      </summary>
      <div className="border-t px-4 py-4">{children}</div>
    </details>
  );
}
