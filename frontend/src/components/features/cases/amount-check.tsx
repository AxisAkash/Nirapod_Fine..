import { formatTaka } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Analysis } from "@/types/api";

export function AmountCheck({ amount, analysis }: { amount: number | null; analysis: Analysis }) {
  const { allowed_fine: allowed, statutory_max: max, statutory_min: min, previous_fine: previous, occurrence, tier } = analysis;
  const checkable = amount != null && allowed != null;
  const scale = checkable ? Math.max(amount, allowed) * 1.12 || 1 : 1;
  const over = checkable && amount > allowed;

  return (
    <div className="grid gap-4">
      {checkable ? (
        <div>
          <p className="text-sm">
            Charged <b>{formatTaka(amount)}</b> <span className="text-muted-foreground">&middot;</span> Allowed <b>{formatTaka(allowed)}</b>
          </p>
          <div
            role="img"
            aria-label={`Charged ${formatTaka(amount)} against an allowed ${formatTaka(allowed)}`}
            className="relative mt-7 mb-1 h-3 rounded-full bg-muted"
          >
            <div className={cn("absolute inset-y-0 left-0 rounded-full", over ? "bg-bad" : "bg-ok")} style={{ width: `${(amount / scale) * 100}%` }} />
            <div className="absolute -top-1.5 -bottom-1.5 w-0.5 bg-foreground" style={{ left: `${(allowed / scale) * 100}%` }}>
              <span className="absolute -top-5 left-1 font-mono text-[0.68rem] whitespace-nowrap">allowed</span>
            </div>
          </div>
          <div className="flex justify-between font-mono text-[0.7rem] text-muted-foreground">
            <span>0</span>
            <span>{formatTaka(Math.round(scale))}</span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">The amount could not be checked automatically for this case.</p>
      )}
      <dl className="grid grid-cols-[8.5rem_1fr] gap-x-3 gap-y-1.5 text-sm">
        <dt className="text-muted-foreground">Statutory max</dt>
        <dd>
          {max == null ? "No Taka ceiling in the source" : formatTaka(max)}
          {tier && <span className="text-muted-foreground"> ({tier})</span>}
          {min ? <span className="text-muted-foreground"> &middot; minimum {formatTaka(min)}</span> : null}
        </dd>
        <dt className="text-muted-foreground">Repeat offence</dt>
        <dd>{previous != null ? `Yes, occurrence ${occurrence}. Previous fine ${formatTaka(previous)}` : analysis.matched_section ? "No earlier case for this section" : "-"}</dd>
        <dt className="text-muted-foreground">Rule applied</dt>
        <dd>{previous != null ? "min(previous fine × 2, maximum)" : "maximum fine"}</dd>
      </dl>
    </div>
  );
}
