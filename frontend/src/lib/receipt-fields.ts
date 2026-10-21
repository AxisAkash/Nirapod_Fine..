import type { Reading } from "@/types/api";

export type ReceiptFieldKey = "reason" | "amount" | "section" | "vehicle" | "date" | "location" | "receipt_number" | "notes";

export const RECEIPT_FIELDS: { key: ReceiptFieldKey; label: string; wide?: boolean }[] = [
  { key: "reason", label: "Offence reason", wide: true },
  { key: "amount", label: "Fine amount (Tk)" },
  { key: "section", label: "Section cited" },
  { key: "vehicle", label: "Vehicle type" },
  { key: "date", label: "Date" },
  { key: "location", label: "Location" },
  { key: "receipt_number", label: "Receipt number" },
  { key: "notes", label: "Notes or claimed exception", wide: true },
];

/** What the AI read from a receipt, as display text. A field it could not find is an empty string. */
export function readingValues(reading: Reading | null | undefined): Record<ReceiptFieldKey, string> {
  const out = Object.fromEntries(RECEIPT_FIELDS.map((f) => [f.key, ""])) as Record<ReceiptFieldKey, string>;
  for (const f of RECEIPT_FIELDS) {
    const v = reading?.fields[f.key]?.value;
    if (v !== null && v !== undefined) out[f.key] = String(v);
  }
  return out;
}
