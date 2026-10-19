"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Loader2 } from "lucide-react";

import { Dropzone } from "@/components/features/upload/dropzone";
import { FieldTag } from "@/components/features/upload/field-tag";
import { ProcessingSteps } from "@/components/features/upload/processing-steps";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { VEHICLE_HINTS } from "@/constants/upload";
import { useAnalysisFlow } from "@/hooks/use-analysis-flow";
import { parseAmountInput } from "@/lib/format";
import { analyzeCase, createManualCase, uploadReceipt } from "@/services/cases.client";
import type { ManualFields, Reading, UploadResult } from "@/types/api";

type FieldKey = "reason" | "amount" | "section" | "vehicle" | "date" | "location" | "receipt_number" | "notes";
type Values = Record<FieldKey, string>;

const EMPTY: Values = { reason: "", amount: "", section: "", vehicle: "", date: "", location: "", receipt_number: "", notes: "" };

interface FieldSpec {
  key: FieldKey;
  label: string;
  placeholder?: string;
  hint?: string;
  type?: string;
  wide?: boolean;
  multiline?: boolean;
}

const FIELDS: FieldSpec[] = [
  { key: "reason", label: "Offence reason", placeholder: "e.g. over speed", hint: "As written on the receipt, in English or Bangla", wide: true },
  { key: "amount", label: "Fine amount (Tk)", placeholder: "e.g. 3000" },
  { key: "section", label: "Section cited", placeholder: "e.g. 87 or ধারা ৮৭", hint: "If the receipt names one" },
  { key: "vehicle", label: "Vehicle type", placeholder: "e.g. motorcycle" },
  { key: "date", label: "Date", type: "date" },
  { key: "location", label: "Location", placeholder: "e.g. Dhaka" },
  { key: "receipt_number", label: "Receipt number" },
  { key: "notes", label: "Notes or claimed exception", hint: "If the driver claimed an exemption, write it here, for example ambulance on emergency duty", wide: true, multiline: true },
];

/** Values the AI read, as form strings. */
function valuesFromReading(reading: Reading): Values {
  const out = { ...EMPTY };
  for (const f of FIELDS) {
    const v = reading.fields[f.key]?.value;
    if (v !== null && v !== undefined) out[f.key] = String(v);
  }
  return out;
}

type Step = "choose" | "reading" | "review";

export function UploadForm() {
  const [step, setStep] = useState<Step>("choose");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [initial, setInitial] = useState<Values>(EMPTY);
  const [v, setV] = useState<Values>(EMPTY);
  const [errors, setErrors] = useState<{ reason?: string; amount?: string }>({});
  const [notice, setNotice] = useState<string | null>(null);
  const flow = useAnalysisFlow();

  // A preview of the chosen image, shown next to the form so the details can be checked against it.
  // It is created when a file is chosen (not in an effect), and released when replaced or when the page closes.
  const previewUrl = useRef<string | null>(null);
  function chooseFile(f: File | null) {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = f && f.type.startsWith("image/") ? URL.createObjectURL(f) : null;
    setPreview(previewUrl.current);
    setFile(f);
  }
  useEffect(
    () => () => {
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    },
    [],
  );

  const set = (k: FieldKey) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));

  async function readReceipt() {
    if (!file) return;
    setStep("reading");
    setNotice(null);
    try {
      const up = await uploadReceipt(file);
      setUpload(up);
      const values = valuesFromReading(up.reading);
      setInitial(values);
      setV(values);
      setNotice(up.reading.message);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "We could not upload this file. Type the details below.");
      setUpload(null);
      setInitial(EMPTY);
      setV(EMPTY);
    }
    setStep("review");
  }

  function startOver() {
    setStep("choose");
    chooseFile(null);
    setUpload(null);
    setV(EMPTY);
    setInitial(EMPTY);
    setErrors({});
    setNotice(null);
    flow.reset();
  }

  function analyse(e: React.FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (!v.reason.trim()) next.reason = "Enter the offence as written on the receipt.";
    if (v.amount.trim() && parseAmountInput(v.amount) === undefined) next.amount = "The fine amount must be a number.";
    setErrors(next);
    if (Object.keys(next).length) return;

    // Send every field, blank ones included: a field you cleared must override what was read from the receipt.
    const fields: ManualFields = { ...v, amount: parseAmountInput(v.amount) ?? "" };
    void flow.run(async (setStage) => {
      setStage("analysing");
      if (upload) {
        await analyzeCase(upload.case_id, fields);
        return upload.case_id;
      }
      return (await createManualCase(fields)).id;
    });
  }

  if (flow.busy) {
    return (
      <div className="rounded-xl border bg-card p-8">
        <h2 className="mb-4 text-center text-xl font-semibold">Checking your receipt</h2>
        <ProcessingSteps stage={flow.stage} withUpload={false} />
      </div>
    );
  }

  if (step === "reading") {
    return (
      <div role="status" className="grid place-items-center gap-3 rounded-xl border bg-card px-6 py-14 text-center">
        <Loader2 className="size-8 animate-spin text-primary" aria-hidden="true" />
        <h2 className="text-xl font-semibold">Reading your receipt</h2>
        <p className="max-w-[46ch] text-sm text-muted-foreground">We are uploading the file and reading the text on it. This usually takes about ten seconds.</p>
      </div>
    );
  }

  if (step === "choose") {
    return (
      <div className="grid gap-4">
        <section className="max-w-2xl rounded-xl border bg-card p-4">
          <h2 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Receipt file</h2>
          <Dropzone file={file} onChange={chooseFile} />
          <p className="mt-3 text-xs text-muted-foreground">
            We read the receipt for you, and you check the details before anything is compared with the law. To read it, the file is sent to an AI service, so only upload receipts you are comfortable sharing. The file is stored with your case.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button size="lg" disabled={!file} onClick={readReceipt}>
              Read receipt
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                setNotice(null);
                setStep("review");
              }}
            >
              Enter the details by hand
            </Button>
          </div>
        </section>
      </div>
    );
  }

  // step === "review"
  const reading = upload?.reading;
  const read = reading?.status === "done";
  return (
    <form onSubmit={analyse} className="grid gap-5" noValidate>
      {(notice || flow.error) && (
        <div role="alert" className={`rounded-lg border px-4 py-3 text-sm ${flow.error || reading?.status === "failed" ? "border-bad bg-bad-bg text-bad" : "border-warn bg-warn-bg text-warn"}`}>
          {flow.error ?? notice}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {upload && file && (
          <section className="h-fit min-w-0 rounded-xl border bg-card p-4 lg:sticky lg:top-20">
            <h2 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Your receipt</h2>
            {preview ? (
              // A local preview of the file the user just chose; there is nothing for the image optimiser to do.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="The receipt you uploaded" className="max-h-[28rem] w-full rounded-lg border bg-muted object-contain" />
            ) : (
              <div className="flex items-center gap-3 rounded-lg border bg-muted p-4">
                <FileText className="size-8 text-primary" aria-hidden="true" />
                <span className="min-w-0 truncate text-sm font-medium">{file.name}</span>
              </div>
            )}
            {read && <p className="mt-3 text-xs text-muted-foreground">Compare each detail with this receipt. Digits in dates and amounts are the easiest thing to misread.</p>}
          </section>
        )}

        <section className={`min-w-0 rounded-xl border bg-card p-4 ${upload && file ? "" : "lg:col-span-2 lg:max-w-3xl"}`}>
          <h2 className="mb-3 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">{read ? "Check the details" : "Receipt details"}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {FIELDS.map((f) => {
              const tag = read ? <FieldTag field={reading?.fields[f.key]} edited={v[f.key] !== initial[f.key]} /> : null;
              const id = `u-${f.key}`;
              return (
                <FormField key={f.key} label={f.label} htmlFor={id} error={errors[f.key as "reason" | "amount"]} hint={f.hint} tag={tag} className={f.wide ? "sm:col-span-2" : ""}>
                  {f.multiline ? (
                    <Textarea id={id} rows={2} value={v[f.key]} onChange={set(f.key)} />
                  ) : (
                    <Input
                      id={id}
                      type={f.type}
                      list={f.key === "vehicle" ? "vehicle-hints" : undefined}
                      inputMode={f.key === "amount" ? "numeric" : undefined}
                      value={v[f.key]}
                      onChange={set(f.key)}
                      placeholder={f.placeholder}
                      aria-invalid={!!errors[f.key as "reason" | "amount"]}
                    />
                  )}
                </FormField>
              );
            })}
            <datalist id="vehicle-hints">
              {VEHICLE_HINTS.map((h) => (
                <option key={h} value={h} />
              ))}
            </datalist>
          </div>
        </section>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg">
          Analyse receipt
        </Button>
        <Button type="button" variant="outline" size="lg" onClick={startOver}>
          Start over
        </Button>
      </div>
    </form>
  );
}
