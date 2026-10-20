"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { Dropzone } from "@/components/features/upload/dropzone";
import { FieldTag } from "@/components/features/upload/field-tag";
import { ProcessingSteps } from "@/components/features/upload/processing-steps";
import { Button } from "@/components/ui/button";
import { useAnalysisFlow } from "@/hooks/use-analysis-flow";
import { cn } from "@/lib/utils";
import { analyzeCase, uploadReceipt } from "@/services/cases.client";
import type { Reading, UploadResult } from "@/types/api";

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

type Status = "empty" | "reading" | "done" | "failed";

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("empty");
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [v, setV] = useState<Values>(EMPTY);
  const [notice, setNotice] = useState<string | null>(null);
  const flow = useAnalysisFlow();

  // A preview of the chosen image, shown beside the details so they can be compared with it.
  // It is created when a file is chosen (not in an effect), and released when replaced or when the page closes.
  const previewUrl = useRef<string | null>(null);
  // Each file gets a token, so a slow answer for a file that has since been replaced or removed is ignored.
  const token = useRef(0);

  useEffect(
    () => () => {
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    },
    [],
  );

  function chooseFile(f: File | null) {
    const mine = ++token.current;
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = f && f.type.startsWith("image/") ? URL.createObjectURL(f) : null;
    setPreview(previewUrl.current);
    setFile(f);
    setUpload(null);
    setV(EMPTY);
    setNotice(null);
    flow.reset();
    if (!f) return setStatus("empty");
    void readReceipt(f, mine);
  }

  // Choosing a file reads it straight away; the details are filled in by the AI and cannot be edited.
  async function readReceipt(f: File, mine: number) {
    setStatus("reading");
    try {
      const up = await uploadReceipt(f);
      if (mine !== token.current) return;
      setUpload(up);
      setV(valuesFromReading(up.reading));
      setNotice(up.reading.message);
      setStatus(up.reading.status === "done" && up.reading.fields.reason?.value ? "done" : "failed");
    } catch (e) {
      if (mine !== token.current) return;
      setNotice(e instanceof Error ? e.message : "We could not upload this file. Try another one.");
      setStatus("failed");
    }
  }

  function analyse(e: React.FormEvent) {
    e.preventDefault();
    if (!upload || status !== "done") return;
    void flow.run(async (setStage) => {
      setStage("analysing");
      await analyzeCase(upload.case_id);
      return upload.case_id;
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

  const reading = upload?.reading;
  const reader = status === "reading";
  const done = status === "done";
  const message = flow.error ?? notice;
  return (
    <form onSubmit={analyse} className="grid gap-4" noValidate>
      {message && (
        <div role="alert" className={`rounded-lg border px-4 py-3 text-sm ${flow.error || status === "failed" ? "border-bad bg-bad-bg text-bad" : "border-warn bg-warn-bg text-warn"}`}>
          {message}
        </div>
      )}

      <div className="grid items-stretch gap-4 lg:grid-cols-2">
        <section className="flex min-w-0 flex-col rounded-xl border bg-card p-5">
          <StepHeading no="1" title="Upload receipt" />
          <Dropzone file={file} onChange={chooseFile} tall={!file} />
          {file && preview && (
            // A local preview of the file the user just chose; there is nothing for the image optimiser to do.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="The receipt you uploaded" className="mt-4 max-h-[26rem] w-full rounded-lg border bg-muted object-contain" />
          )}
          <p className="mt-auto pt-4 text-xs leading-relaxed text-muted-foreground">
            The receipt is read by AI as soon as you choose it. The file is sent to an AI service and stored with your case, so only upload receipts you are comfortable sharing.
          </p>
        </section>

        <section className="flex min-w-0 flex-col rounded-xl border bg-card p-5" aria-busy={reader}>
          <div className="mb-4 flex items-center justify-between gap-2">
            <StepHeading no="2" title="Extracted details" className="mb-0" />
            {reader && (
              <span role="status" className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin text-primary" aria-hidden="true" />
                Reading&hellip;
              </span>
            )}
            {done && <span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-[0.68rem] text-muted-foreground">Read-only</span>}
          </div>
          <dl className="grid flex-1 content-start gap-x-6 gap-y-4 sm:grid-cols-2">
            {FIELDS.map((f) => {
              const value = v[f.key].trim();
              return (
                <div key={f.key} className={cn("min-w-0 border-b pb-3", f.wide && "sm:col-span-2")}>
                  <dt className="mb-1 flex items-center justify-between gap-2 text-xs font-medium text-muted-foreground">
                    {f.label}
                    {done && <FieldTag field={reading?.fields[f.key]} edited={false} />}
                  </dt>
                  <dd className={cn("min-h-6 text-[0.95rem] break-words whitespace-pre-wrap", value ? "font-medium text-foreground" : "text-muted-foreground/60", reader && "animate-pulse")}>{value || "\u2014"}</dd>
                </div>
              );
            })}
          </dl>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
            <p className="max-w-[44ch] text-xs text-muted-foreground">
              {done ? "Check these against your receipt. If something is wrong, remove the file and upload a clearer picture." : "The details appear here once the receipt has been read. They cannot be edited."}
            </p>
            <Button type="submit" size="lg" disabled={!done}>
              Analyse receipt
            </Button>
          </div>
        </section>
      </div>
    </form>
  );
}

function StepHeading({ no, title, className }: { no: string; title: string; className?: string }) {
  return (
    <h2 className={cn("mb-4 flex items-center gap-2.5 text-base font-semibold", className)}>
      <span aria-hidden="true" className="grid size-6 place-items-center rounded-full bg-primary font-mono text-xs text-primary-foreground">
        {no}
      </span>
      {title}
    </h2>
  );
}
