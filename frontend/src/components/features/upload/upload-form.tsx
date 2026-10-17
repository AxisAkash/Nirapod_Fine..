"use client";

import { useState } from "react";

import { Dropzone } from "@/components/features/upload/dropzone";
import { ProcessingSteps } from "@/components/features/upload/processing-steps";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { VEHICLE_HINTS } from "@/constants/upload";
import { useAnalysisFlow } from "@/hooks/use-analysis-flow";
import { parseAmountInput } from "@/lib/format";
import { analyzeCase, createManualCase, uploadReceipt } from "@/services/cases.client";
import type { ManualFields } from "@/types/api";

const EMPTY = { reason: "", amount: "", section: "", vehicle: "", date: "", location: "", receipt_number: "", notes: "" };

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [v, setV] = useState(EMPTY);
  const [errors, setErrors] = useState<{ reason?: string; amount?: string }>({});
  const flow = useAnalysisFlow();
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (!v.reason.trim()) next.reason = "Enter the offence as written on the receipt.";
    if (v.amount.trim() && parseAmountInput(v.amount) === undefined) next.amount = "The fine amount must be a number.";
    setErrors(next);
    if (Object.keys(next).length) return;

    const fields: ManualFields = { ...v, amount: parseAmountInput(v.amount) };
    void flow.run(async (setStage) => {
      if (file) {
        setStage("uploading");
        const up = await uploadReceipt(file, fields);
        setStage("analysing");
        await analyzeCase(up.case_id);
        return up.case_id;
      }
      setStage("analysing");
      return (await createManualCase(fields)).id;
    });
  }

  if (flow.busy) {
    return (
      <div className="rounded-xl border bg-card p-8">
        <h2 className="mb-4 text-center text-xl font-semibold">Checking your receipt</h2>
        <ProcessingSteps stage={flow.stage} withUpload={!!file} />
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-6" noValidate>
      {flow.error && (
        <div role="alert" className="rounded-lg border border-bad bg-bad-bg px-4 py-3 text-sm text-bad">
          {flow.error}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border bg-card p-4">
          <h2 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">1 &middot; Receipt file</h2>
          <Dropzone file={file} onChange={setFile} />
          <p className="mt-3 text-xs text-muted-foreground">
            The file is stored with your case and shown on the case record. You can also continue without a file by typing the details.
          </p>
        </section>

        <section className="rounded-xl border bg-card p-4">
          <h2 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">2 &middot; Receipt details</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Offence reason" htmlFor="u-reason" error={errors.reason} hint="As written on the receipt, in English or Bangla" className="sm:col-span-2">
              <Input id="u-reason" value={v.reason} onChange={set("reason")} aria-invalid={!!errors.reason} placeholder="e.g. over speed" />
            </FormField>
            <FormField label="Fine amount (Tk)" htmlFor="u-amount" error={errors.amount}>
              <Input id="u-amount" inputMode="numeric" value={v.amount} onChange={set("amount")} aria-invalid={!!errors.amount} placeholder="e.g. 3000" />
            </FormField>
            <FormField label="Section cited" htmlFor="u-section" hint="If the receipt names one">
              <Input id="u-section" value={v.section} onChange={set("section")} placeholder="e.g. 87 or ধারা ৮৭" />
            </FormField>
            <FormField label="Vehicle type" htmlFor="u-vehicle">
              <Input id="u-vehicle" list="vehicle-hints" value={v.vehicle} onChange={set("vehicle")} placeholder="e.g. motorcycle" />
              <datalist id="vehicle-hints">
                {VEHICLE_HINTS.map((h) => (
                  <option key={h} value={h} />
                ))}
              </datalist>
            </FormField>
            <FormField label="Date" htmlFor="u-date">
              <Input id="u-date" type="date" value={v.date} onChange={set("date")} />
            </FormField>
            <FormField label="Location" htmlFor="u-location">
              <Input id="u-location" value={v.location} onChange={set("location")} placeholder="e.g. Dhaka" />
            </FormField>
            <FormField label="Receipt number" htmlFor="u-number">
              <Input id="u-number" value={v.receipt_number} onChange={set("receipt_number")} />
            </FormField>
            <FormField
              label="Notes or claimed exception"
              htmlFor="u-notes"
              hint="If the driver claimed an exemption, write it here, for example ambulance on emergency duty"
              className="sm:col-span-2"
            >
              <Textarea id="u-notes" rows={2} value={v.notes} onChange={set("notes")} />
            </FormField>
          </div>
        </section>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg">
          Analyse receipt
        </Button>
        <Button
          type="button"
          variant="outline"
          size="lg"
          onClick={() => {
            setV(EMPTY);
            setFile(null);
            setErrors({});
            flow.reset();
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
