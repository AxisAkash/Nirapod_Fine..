"use client";

import { useEffect } from "react";
import { FileText } from "lucide-react";

import { ReceiptDetails } from "@/components/features/upload/receipt-details";
import { ProcessingSteps } from "@/components/features/upload/processing-steps";
import type { ReadReceipt } from "@/components/features/upload/upload-panel";
import { Button } from "@/components/ui/button";
import { useAnalysisFlow } from "@/hooks/use-analysis-flow";
import { analyzeCase } from "@/services/cases.client";

/** The receipt beside the details the AI read from it. Nothing can be edited; the user analyses or starts again. */
export function ReviewStep({ receipt, onReset }: { receipt: ReadReceipt; onReset: () => void }) {
  const flow = useAnalysisFlow();
  const { previewUrl } = receipt;

  // The local preview is released when the user starts over or leaves.
  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  if (flow.busy) {
    return (
      <div className="py-4">
        <h3 className="mb-3 text-center text-lg font-semibold">Checking your receipt</h3>
        <ProcessingSteps stage={flow.stage} withUpload={false} />
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <section aria-label="Your receipt" className="min-w-0 rounded-lg border bg-background p-4">
          <h3 className="mb-3 text-base font-semibold">Your receipt</h3>
          {previewUrl ? (
            // A local preview of the file the user just chose; there is nothing for the image optimiser to do.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt="The receipt you uploaded" className="max-h-[30rem] w-full rounded-lg border bg-muted object-contain" />
          ) : (
            <div className="flex items-center gap-3 rounded-lg border bg-muted p-4">
              <FileText aria-hidden="true" className="size-8 shrink-0 text-primary" />
              <span className="min-w-0 truncate text-sm font-medium">{receipt.file.name}</span>
            </div>
          )}
          <p className="mt-3 truncate text-xs text-muted-foreground">{receipt.file.name}</p>
        </section>

        <section aria-label="Details read by AI" className="grid min-w-0 gap-4 rounded-lg border bg-background p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-semibold">Details read by AI</h3>
            <span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-[0.68rem] text-muted-foreground">Read-only</span>
          </div>
          <ReceiptDetails reading={receipt.reading} />
          <p className="text-xs text-muted-foreground">Check these against your receipt. If something is wrong, use a different receipt with a clearer picture.</p>
        </section>
      </div>

      {flow.error && (
        <p role="alert" className="text-sm text-bad">
          {flow.error}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          size="lg"
          onClick={() =>
            void flow.run(async (setStage) => {
              setStage("analysing");
              await analyzeCase(receipt.caseId);
              return receipt.caseId;
            })
          }
        >
          Analyse receipt
        </Button>
        <Button variant="outline" size="lg" onClick={onReset}>
          Use a different receipt
        </Button>
      </div>
    </div>
  );
}
