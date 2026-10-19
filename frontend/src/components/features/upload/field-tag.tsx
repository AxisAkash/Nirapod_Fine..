import { cn } from "@/lib/utils";
import type { ReadField } from "@/types/api";

/** A small label beside a form field that says how sure we are about a value read from the receipt. */
export function FieldTag({ field, edited }: { field: ReadField | undefined; edited: boolean }) {
  if (!field || edited || field.status === "missing") return null;
  const check = field.status === "unverified";
  return (
    <span
      title={field.note ?? (check ? "This could not be confirmed in the text read from the receipt." : undefined)}
      className={cn("rounded-full px-2 py-0.5 font-mono text-[0.66rem] whitespace-nowrap", check ? "bg-warn-bg text-warn" : "bg-muted text-muted-foreground")}
    >
      {check ? "Check this" : "Read from receipt"}
    </span>
  );
}
