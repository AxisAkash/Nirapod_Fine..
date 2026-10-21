import { JUSTIFICATION_STRIPE } from "@/constants/status";
import { describeScoreLine } from "@/lib/cases";
import { cn } from "@/lib/utils";
import type { Justification } from "@/types/api";

export function JustificationList({ items }: { items: Justification[] }) {
  return (
    <ul className="grid gap-3">
      {items.map((j, i) => (
        <li key={`${j.title}-${i}`} className={cn("border-l-[3px] py-0.5 pl-3 text-sm", JUSTIFICATION_STRIPE[j.tone] ?? "border-border")}>
          <p className="font-medium">{j.title}</p>
          <p className="text-foreground/90">{j.text}</p>
          {j.meta && (
            <ul className="mt-1 grid gap-0.5 text-xs text-muted-foreground">
              {describeScoreLine(j.meta).map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
