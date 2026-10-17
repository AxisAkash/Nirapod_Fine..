import { formatDate, formatTaka } from "@/lib/format";
import type { CaseExtracted } from "@/types/api";

export function ExtractedFields({ data }: { data: CaseExtracted }) {
  const rows: [string, string][] = [
    ["Reason", data.reason ?? "-"],
    ["Fine", formatTaka(data.amount)],
    ["Date", formatDate(data.date)],
    ["Location", data.location ?? "-"],
    ["Vehicle", data.vehicle_type ?? "-"],
    ["Receipt no.", data.receipt_number ?? "-"],
    ["Section cited", data.section ?? "not stated"],
  ];
  if (data.notes) rows.push(["Notes", data.notes]);
  return (
    <dl className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1.5 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted-foreground">{k}</dt>
          <dd className="min-w-0 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
