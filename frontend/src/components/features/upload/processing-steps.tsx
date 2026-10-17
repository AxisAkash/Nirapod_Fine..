import { cn } from "@/lib/utils";
import type { FlowStage } from "@/hooks/use-analysis-flow";

interface Step {
  id: FlowStage;
  label: string;
  detail?: string;
}

/** Shows the real stages of the request: upload, analysis, then opening the result. */
export function ProcessingSteps({ stage, withUpload }: { stage: FlowStage; withUpload: boolean }) {
  const steps: Step[] = [
    ...(withUpload ? [{ id: "uploading" as const, label: "Uploading the receipt", detail: "The file is stored and hashed." }] : []),
    {
      id: "analysing",
      label: "Analysing the case",
      detail: "Matching the offence to a section, checking the fine and the repeat history, and testing exception rules.",
    },
    { id: "done", label: "Opening your result" },
  ];
  const order = steps.map((s) => s.id);
  const current = order.indexOf(stage);

  return (
    <ol className="mx-auto grid max-w-lg gap-1" aria-live="polite">
      {steps.map((s, i) => {
        const state = i < current ? "done" : i === current ? "active" : "todo";
        return (
          <li key={s.id} className={cn("grid grid-cols-[1.5rem_1fr] gap-3 py-2", state === "todo" && "text-muted-foreground")}>
            <span
              aria-hidden="true"
              className={cn(
                "mt-0.5 block size-5 rounded-full border-2",
                state === "done" && "border-ok bg-ok",
                state === "active" && "animate-spin border-primary border-t-transparent",
                state === "todo" && "border-border",
              )}
            />
            <span>
              <span className="block text-sm font-medium">{s.label}</span>
              {s.detail && state !== "todo" && <span className="block text-xs text-muted-foreground">{s.detail}</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
