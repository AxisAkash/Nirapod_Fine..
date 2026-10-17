import type { Analysis } from "@/types/api";

export function MatchedSection({ analysis, confidenceLabel = "Confidence" }: { analysis: Analysis; confidenceLabel?: string }) {
  const { matched_section: section, matched_title: title, matched_category: category, confidence, candidates } = analysis;
  return (
    <div className="grid gap-3">
      {section ? (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-heading text-lg font-semibold">
              Section {section}: {title}
            </p>
            {category && <p className="text-sm text-muted-foreground">Category: {category}</p>}
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <span>{confidenceLabel} {confidence}%</span>
            <span className="block h-1.5 w-28 overflow-hidden rounded-full bg-muted" role="presentation">
              <span className="block h-full bg-primary" style={{ width: `${Math.min(confidence, 100)}%` }} />
            </span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No section could be selected for this offence.</p>
      )}
      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-primary">Show candidate sections and scores</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="font-mono text-xs text-muted-foreground uppercase">
              <tr>
                <th className="py-1.5 pr-3 font-medium">Section</th>
                <th className="py-1.5 pr-3 font-medium">Offence</th>
                <th className="py-1.5 pr-3 text-right font-medium">Reason</th>
                <th className="py-1.5 pr-3 text-right font-medium">Cited</th>
                <th className="py-1.5 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
                <tr key={c.section} className="border-t align-top">
                  <td className="py-2 pr-3 font-mono">{c.section}</td>
                  <td className="py-2 pr-3">
                    {c.title}
                    <span className="block text-xs text-muted-foreground">{c.why.join(" · ") || "no signals"}</span>
                  </td>
                  <td className="py-2 pr-3 text-right font-mono tabular-nums">{c.reason_score}</td>
                  <td className="py-2 pr-3 text-right font-mono tabular-nums">{c.section_score}</td>
                  <td className="py-2 text-right font-mono tabular-nums">{c.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
