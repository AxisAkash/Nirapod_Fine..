"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

export type FlowStage = "idle" | "uploading" | "analysing" | "done" | "error";

/**
 * Runs a multi-step "create a case, then analyse it" task, reports which step is in progress, and opens the
 * result page when it finishes. The task receives `setStage` so it can report real progress.
 */
export function useAnalysisFlow() {
  const router = useRouter();
  const [stage, setStage] = useState<FlowStage>("idle");
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (task: (setStage: (s: FlowStage) => void) => Promise<string>) => {
      setError(null);
      try {
        const caseId = await task(setStage);
        setStage("done");
        router.push(`/cases/${caseId}/result`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
        setStage("error");
      }
    },
    [router],
  );

  const reset = useCallback(() => {
    setStage("idle");
    setError(null);
  }, []);

  return { stage, error, run, reset, busy: stage === "uploading" || stage === "analysing" || stage === "done" };
}
