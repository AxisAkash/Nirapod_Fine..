import { ReceiptPaper } from "@/components/features/cases/receipt-paper";
import { shortHash } from "@/lib/format";
import type { CaseDetail } from "@/types/api";

/** The uploaded file, served through the authenticated proxy. */
export function ReceiptPreview({ receipt, extracted }: { receipt: CaseDetail["receipt"]; extracted: CaseDetail["extracted"] }) {
  if (!receipt) return <ReceiptPaper data={extracted} />;
  const src = `/api/backend/receipts/${receipt.id}/file`;
  const isImage = receipt.file_type?.startsWith("image/");
  return (
    <div className="grid gap-3">
      {isImage ? (
        // The file comes from an authenticated route, so Next's image optimiser cannot fetch it.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={`Uploaded receipt ${receipt.file_name ?? ""}`} className="max-h-96 w-full rounded-lg border bg-muted object-contain" />
      ) : (
        <a href={src} target="_blank" rel="noreferrer" className="rounded-lg border bg-muted p-6 text-center text-sm font-medium text-primary hover:underline">
          Open the PDF receipt
        </a>
      )}
      <dl className="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">File</dt>
        <dd className="break-all">{receipt.file_name ?? "-"}</dd>
        <dt className="text-muted-foreground">File hash</dt>
        <dd className="font-mono text-xs break-all" title={receipt.file_hash ?? undefined}>
          {receipt.file_hash ?? shortHash(null)}
        </dd>
      </dl>
    </div>
  );
}
