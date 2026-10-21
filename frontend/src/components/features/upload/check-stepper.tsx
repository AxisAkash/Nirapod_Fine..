import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

const STEPS = ["Upload", "Review", "Result"];

/** Where the user is in checking a receipt. `current` is 1, 2 or 3. */
export function CheckStepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <ol aria-label="Progress" className="flex items-center gap-2 text-sm">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <li key={label} aria-current={active ? "step" : undefined} className="flex items-center gap-2">
            <span
              className={cn(
                "grid size-6 place-items-center rounded-full border text-xs font-medium",
                done && "border-primary bg-primary text-primary-foreground",
                active && "border-primary text-primary",
                !done && !active && "text-muted-foreground",
              )}
            >
              {done ? <Check aria-hidden="true" className="size-3.5" /> : n}
            </span>
            <span className={cn("font-medium", !active && !done && "text-muted-foreground")}>{label}</span>
            {n < STEPS.length && <span aria-hidden="true" className="mx-1 h-px w-8 bg-border sm:w-12" />}
          </li>
        );
      })}
    </ol>
  );
}
