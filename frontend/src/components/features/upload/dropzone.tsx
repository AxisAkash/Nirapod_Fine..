"use client";

import { useRef, useState } from "react";
import { FileText, ImageIcon, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ACCEPT_ATTR, ACCEPTED_TYPES, MAX_UPLOAD_MB } from "@/constants/upload";
import { cn } from "@/lib/utils";

export function Dropzone({ file, onChange }: { file: File | null; onChange: (f: File | null) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [error, setError] = useState<string>();

  function accept(f: File | undefined) {
    if (!f) return;
    if (!ACCEPTED_TYPES.includes(f.type)) return setError("Choose a JPG, PNG or PDF file.");
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return setError(`The file is larger than ${MAX_UPLOAD_MB} MB.`);
    setError(undefined);
    onChange(f);
  }

  if (file) {
    const Icon = file.type === "application/pdf" ? FileText : ImageIcon;
    return (
      <div className="flex items-center gap-3 rounded-lg border bg-muted p-3">
        <Icon className="size-8 shrink-0 text-primary" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(0)} KB</p>
        </div>
        <Button type="button" variant="ghost" size="icon" aria-label="Remove file" onClick={() => onChange(null)}>
          <X />
        </Button>
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          accept(e.dataTransfer.files[0]);
        }}
        className={cn(
          "flex w-full flex-col items-center gap-1 rounded-lg border-2 border-dashed bg-muted px-4 py-8 text-center text-sm text-muted-foreground transition-colors hover:border-primary",
          over && "border-primary bg-accent",
        )}
      >
        <Upload className="mb-1 size-6 text-primary" aria-hidden="true" />
        <span className="font-medium text-foreground">Drop a JPG, PNG or PDF here</span>
        <span>or click to choose a file &middot; up to {MAX_UPLOAD_MB} MB</span>
      </button>
      <input ref={input} type="file" accept={ACCEPT_ATTR} className="sr-only" tabIndex={-1} aria-label="Receipt file" onChange={(e) => accept(e.target.files?.[0])} />
      {error && (
        <p role="alert" className="mt-2 text-sm text-bad">
          {error}
        </p>
      )}
    </div>
  );
}
