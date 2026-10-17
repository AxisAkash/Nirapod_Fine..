"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { analyzeCase } from "@/services/cases.client";

export function AnalyzeNow({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try {
      await analyzeCase(caseId);
      router.refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not analyse this case.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Button onClick={run} disabled={busy}>
      {busy ? "Analysing…" : "Analyse now"}
    </Button>
  );
}
