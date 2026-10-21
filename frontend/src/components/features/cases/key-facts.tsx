import { formatTaka } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Analysis } from "@/types/api";

/** The four numbers that answer "was this fine right?", shown right under the verdict. */
export function KeyFacts({ amount, analysis }: { amount: number | null; analysis: Analysis }) {
  const { matched_section: section, matched_title: title, allowed_fine: allowed } = analysis;
  const checkable = amount != null && allowed != null;
  const diff = checkable ? amount - allowed : null;

  const facts: { label: string; value: string; note?: string; tone?: "ok" | "bad" }[] = [
    { label: "Legal section", value: section ? `Section ${section}` : "Not matched", note: title ?? undefined },
    { label: "Amount charged", value: amount != null ? formatTaka(amount) : "Not found" },
    { label: "Amount allowed", value: allowed != null ? formatTaka(allowed) : "Not set", note: analysis.previous_fine != null ? "Repeat offence" : "Statutory maximum" },
    diff == null
      ? { label: "Difference", value: "Cannot be checked" }
      : diff > 0
        ? { label: "Difference", value: `${formatTaka(diff)} over`, tone: "bad" }
        : { label: "Difference", value: "Within the limit", tone: "ok" },
  ];

  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {facts.map((f) => (
        <div key={f.label} className="min-w-0 rounded-xl border bg-card px-4 py-3">
          <dt className="font-mono text-[0.68rem] tracking-wider text-muted-foreground uppercase">{f.label}</dt>
          <dd className={cn("mt-1 text-lg leading-snug font-semibold", f.tone === "bad" && "text-bad", f.tone === "ok" && "text-ok")}>{f.value}</dd>
          {f.note && <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{f.note}</p>}
        </div>
      ))}
    </dl>
  );
}
