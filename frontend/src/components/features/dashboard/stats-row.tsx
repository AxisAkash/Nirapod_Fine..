import { countGroups } from "@/lib/cases";
import type { CaseListItem } from "@/types/api";

export function StatsRow({ cases }: { cases: CaseListItem[] }) {
  const n = countGroups(cases);
  const stats = [
    { label: "Total checks", value: n.all, color: "text-foreground" },
    { label: "Consistent results", value: n.consistent, color: "text-ok" },
    { label: "Review required", value: n.review, color: "text-warn" },
  ];
  return (
    <dl className="grid gap-2.5 sm:grid-cols-3">
      {stats.map((s) => (
        <div key={s.label} className="rounded-lg border bg-card px-3.5 py-3">
          <dt className="text-[0.78rem] text-muted-foreground">{s.label}</dt>
          <dd className={`mt-0.5 font-mono text-[1.35rem] font-semibold tabular-nums ${s.color}`}>{s.value}</dd>
        </div>
      ))}
    </dl>
  );
}
