import { RECEIPT_FIELDS, readingValues } from "@/lib/receipt-fields";
import { cn } from "@/lib/utils";
import type { Reading } from "@/types/api";

/** The details the AI read from a receipt, as read-only text. Nothing here can be edited. */
export function ReceiptDetails({ reading }: { reading: Reading | null | undefined }) {
  const values = readingValues(reading);
  return (
    <dl className="grid content-start gap-x-6 gap-y-4 sm:grid-cols-2">
      {RECEIPT_FIELDS.map((f) => {
        const value = values[f.key].trim();
        return (
          <div key={f.key} className={cn("min-w-0 border-b pb-3", f.wide && "sm:col-span-2")}>
            <dt className="mb-1 text-xs font-medium text-muted-foreground">{f.label}</dt>
            <dd className={cn("min-h-6 text-[0.95rem] break-words whitespace-pre-wrap", value ? "font-medium text-foreground" : "text-muted-foreground/60")}>{value || "—"}</dd>
          </div>
        );
      })}
    </dl>
  );
}
