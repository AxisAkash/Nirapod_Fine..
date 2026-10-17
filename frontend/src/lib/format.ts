const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Backend timestamps are naive UTC; mark them as UTC so the browser converts them correctly. */
function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : parseUtc(iso);
  return Number.isNaN(d.getTime()) ? "-" : dateFmt.format(d);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = parseUtc(iso);
  return Number.isNaN(d.getTime()) ? "-" : dateTimeFmt.format(d);
}

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** "Tk 15,000", or a dash when there is no amount. */
export function formatTaka(n: number | null | undefined): string {
  return n == null ? "-" : `Tk ${formatNumber(n)}`;
}

export function shortHash(h: string | null | undefined): string {
  return h ? `${h.slice(0, 8)}…${h.slice(-6)}` : "-";
}

/** Digits only, accepting Bangla digits and thousands separators. Empty input gives undefined. */
export function parseAmountInput(value: string): number | undefined {
  const ascii = value.replace(/[০-৯]/g, (d) => String(d.charCodeAt(0) - 0x09e6));
  const digits = ascii.replace(/[^\d]/g, "");
  return digits ? Number(digits) : undefined;
}

/** Numeric ordering for sections like "89(1)" so they sort 89(1), 89(2), 90. */
export function compareSections(a: string, b: string): number {
  const num = (s: string) => Number(s.split("(")[0]);
  return num(a) - num(b) || a.localeCompare(b);
}
