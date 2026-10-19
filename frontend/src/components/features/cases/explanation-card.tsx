import { NeutralPill } from "@/components/ui/result-pill";
import type { Analysis } from "@/types/api";

/** The explanation text, with a clear label of who wrote it. */
export function ExplanationBody({ text, analysis }: { text: string | null; analysis: Analysis | null }) {
  const ai = analysis?.explanation?.source === "ai";
  return (
    <>
      <div className="mb-2">
        <NeutralPill title={ai && analysis?.explanation?.model ? `Written by ${analysis.explanation.model}` : undefined}>{ai ? "Written by AI" : "Standard explanation"}</NeutralPill>
      </div>
      <p className="rounded-lg bg-muted px-4 py-3 text-sm">{text ?? "No explanation yet."}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        {ai
          ? "Written by an AI model from the matched rules only, then checked: it cannot mention a section or amount that the rules did not produce. The result itself never comes from the AI."
          : "Written from the matched rules only. It never cites a section that was not matched."}
      </p>
    </>
  );
}
