import { STATUS_META, TONE_STYLES } from "@/constants/status";
import { cn } from "@/lib/utils";
import type { ValidationStatus } from "@/types/api";

export function StatusBadge({ status, className }: { status: ValidationStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <span className={cn("inline-block rounded-full px-2.5 py-0.5 font-mono text-xs whitespace-nowrap", TONE_STYLES[meta.tone].soft, className)}>
      {meta.label}
    </span>
  );
}
