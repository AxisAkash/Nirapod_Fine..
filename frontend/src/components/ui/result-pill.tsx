import { groupOf, RESULT_GROUPS, TONE_STYLES } from "@/constants/status";
import { cn } from "@/lib/utils";
import type { ValidationStatus } from "@/types/api";

/** The three-group result label (Consistent, Review Required, Insufficient Information). */
export function ResultPill({ status, className }: { status: ValidationStatus; className?: string }) {
  const g = RESULT_GROUPS[groupOf(status)];
  return <span className={cn("inline-block rounded-full px-2.5 py-0.5 font-mono text-xs whitespace-nowrap", TONE_STYLES[g.tone].soft, className)}>{g.label}</span>;
}

export function NeutralPill({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <span title={title} className="inline-block rounded-full bg-muted px-2.5 py-0.5 font-mono text-xs whitespace-nowrap text-muted-foreground">
      {children}
    </span>
  );
}
