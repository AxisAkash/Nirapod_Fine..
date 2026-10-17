import Link from "next/link";

import { cn } from "@/lib/utils";

const TABS = [
  { id: "versions", label: "Dataset versions" },
  { id: "rules", label: "Offence rules" },
  { id: "exceptions", label: "Exception rules" },
];

export function AdminTabs({ current, versionId }: { current: string; versionId: string }) {
  return (
    <nav aria-label="Admin sections" className="flex flex-wrap gap-1.5">
      {TABS.map((t) => (
        <Link
          key={t.id}
          href={`/admin/dataset?tab=${t.id}&version=${versionId}`}
          aria-current={current === t.id ? "page" : undefined}
          className={cn(
            "rounded-md border bg-card px-3.5 py-1.5 text-sm font-medium transition-colors hover:bg-muted",
            current === t.id && "border-primary bg-primary text-primary-foreground hover:bg-primary",
          )}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
