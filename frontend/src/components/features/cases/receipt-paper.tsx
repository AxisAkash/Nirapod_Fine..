import { formatTaka } from "@/lib/format";
import type { CaseExtracted } from "@/types/api";

function Line({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="shrink-0 text-[#6b6657]">{k}</span>
      <span className="text-right break-words">{v}</span>
    </div>
  );
}

/** A receipt-style summary of the notice details. Used where there is no uploaded file to show. */
export function ReceiptPaper({ data }: { data: CaseExtracted }) {
  const rows: [string, string][] = [
    ["Receipt no.", data.receipt_number ?? "-"],
    ["Date", data.date ?? "-"],
    ["Location", data.location ?? "-"],
    ["Vehicle", data.vehicle_type ?? "-"],
    ["Section cited", data.section ?? "not stated"],
  ];
  return (
    <div className="relative rounded border border-[#cfc9b6] bg-paper px-[18px] py-4 font-mono text-[0.86rem] leading-normal text-paper-ink shadow-[2px_3px_0_rgba(0,0,0,0.06)]">
      <h5 className="mb-0.5 text-center font-heading text-[0.95rem] font-semibold">Traffic Case Receipt &middot; ট্রাফিক মামলা রশিদ</h5>
      <div className="mb-2.5 text-center text-[0.72rem] text-[#6b6657]">Metropolitan Traffic Magistrate, mobile court</div>
      {rows.map(([k, v]) => (
        <Line key={k} k={k} v={v} />
      ))}
      <hr className="my-2 border-0 border-t border-dashed border-[#b9b29a]" />
      <Line k="Offence" v={data.reason ?? "-"} />
      {data.notes && <Line k="Notes" v={data.notes} />}
      <hr className="my-2 border-0 border-t border-dashed border-[#b9b29a]" />
      <Line k="Fine (Tk)" v={<b>{data.amount == null ? "-" : formatTaka(data.amount).replace("Tk ", "")}</b>} />
      <div className="mt-2.5 text-center text-[0.66rem] tracking-[0.1em] text-[#8c8670]">RECEIPT COPY</div>
    </div>
  );
}
