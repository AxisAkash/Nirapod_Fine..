"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Dropzone } from "@/components/features/upload/dropzone";
import { Button } from "@/components/ui/button";
import { uploadReceipt } from "@/services/cases.client";
import type { Reading } from "@/types/api";

/** A receipt that has been uploaded and read, ready to be reviewed. */
export interface ReadReceipt {
  caseId: string;
  file: File;
  previewUrl: string | null;
  reading: Reading;
}

/** Choose a receipt on the Overview page. It is uploaded and read here, then handed on for review. */
export function UploadPanel({ onRead }: { onRead: (receipt: ReadReceipt) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start(f: File | null) {
    if (!f) return;
    setFile(f);
    setError(null);
    setWorking(true);
    try {
      const up = await uploadReceipt(f);
      const reading = up.reading;
      if (reading.status !== "done" || !reading.fields.reason?.value) {
        setError(reading.message ?? "We could not read the details on this receipt. Try a clearer picture.");
        setWorking(false);
        return;
      }
      onRead({ caseId: up.case_id, file: f, previewUrl: f.type.startsWith("image/") ? URL.createObjectURL(f) : null, reading });
    } catch (e) {
      setError(e instanceof Error ? e.message : "We could not upload this file. Try again.");
      setWorking(false);
    }
  }

  if (working && file) {
    return (
      <div role="status" aria-live="polite" className="grid place-items-center gap-2 rounded-lg border bg-background px-4 py-10 text-center">
        <Loader2 aria-hidden="true" className="size-8 animate-spin text-primary" />
        <p className="font-medium">Reading your receipt&hellip;</p>
        <p className="max-w-[46ch] truncate text-sm text-muted-foreground">{file.name}</p>
        <p className="max-w-[46ch] text-xs text-muted-foreground">We are uploading the file and reading the text on it. This usually takes about ten seconds.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      <Dropzone file={null} onChange={start} tall />
      {error && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-bad bg-bad-bg px-4 py-3 text-sm text-bad">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={() => setError(null)}>
            Try another file
          </Button>
        </div>
      )}
      <p className="text-xs text-muted-foreground">The file is sent to an AI service to be read and is stored with your case, so only upload receipts you are comfortable sharing.</p>
    </div>
  );
}
