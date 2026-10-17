import { STATUS_META, TONE_STYLES } from "@/constants/status";
import { ResultPill } from "@/components/ui/result-pill";
import { cn } from "@/lib/utils";
import type { ValidationStatus } from "@/types/api";

export function VerdictBanner({ status, summary, flags }: { status: ValidationStatus; summary: string | null; flags: string[] }) {
  const meta = STATUS_META[status];
  const tone = TONE_STYLES[meta.tone];
  return (
    <section aria-label="Verdict" className={cn("flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-xl border px-5 py-4", tone.soft, tone.border)}>
      <div className="min-w-0 flex-1 basis-80">
        <p className="font-mono text-xs tracking-wider uppercase opacity-80">Verdict</p>
        <h2 className="text-2xl font-semibold">{meta.headline}</h2>
        {summary && <p className="mt-1 text-sm text-foreground/80">{summary}</p>}
      </div>
      <div className="flex flex-col items-start gap-1.5 sm:items-end">
        <ResultPill status={status} className="bg-card/70" />
        <span className="font-mono text-xs text-muted-foreground">{status}</span>
        {flags.length > 0 && (
          <ul className="flex flex-wrap gap-1.5 sm:justify-end">
            {flags.map((f) => (
              <li key={f} className="rounded-full bg-card/70 px-2.5 py-0.5 text-xs text-foreground">
                {f}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
