"use client";

import { useState } from "react";

import { EFFECTS, ExceptionEditor } from "@/components/features/admin/exception-editor";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { AdminException, AdminVersion } from "@/types/api";

const EFFECT_STYLE: Record<string, string> = {
  exempts: "bg-ok-bg text-ok",
  permission_based: "bg-warn-bg text-warn",
  no_general_exemption: "bg-muted text-muted-foreground",
  repealed: "bg-muted text-muted-foreground",
};

export function ExceptionsPanel({ version, rules }: { version: AdminVersion; rules: AdminException[] }) {
  const [selected, setSelected] = useState<AdminException | null>(null);
  const [adding, setAdding] = useState(false);
  const readOnly = version.status !== "draft";

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Viewing <b className="text-foreground">{version.version_name}</b>. Each exception has an effect and a scope limit, and the engine enforces both.
        </p>
        {!readOnly && <Button onClick={() => setAdding(true)}>Add exception</Button>}
      </div>
      <ul className="grid gap-3">
        {rules.map((x) => (
          <li key={x.id} className="rounded-xl border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="min-w-0 flex-1 font-medium">{x.exception_title}</p>
              <span className={cn("rounded-full px-2.5 py-0.5 font-mono text-xs", EFFECT_STYLE[x.effect ?? ""] ?? "bg-muted")}>{x.effect}</span>
            </div>
            <dl className="mt-2 grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1 text-sm">
              <dt className="text-muted-foreground">Applies to</dt>
              <dd>{x.applies_to_section ? `Section ${x.applies_to_section}` : x.applies_to_category === "*" ? "any offence" : `category: ${x.applies_to_category}`}</dd>
              <dt className="text-muted-foreground">Vehicles</dt>
              <dd>{x.vehicle_types.length ? x.vehicle_types.join(", ") : "any"}</dd>
              <dt className="text-muted-foreground">Scope limit</dt>
              <dd>{x.scope_limit}</dd>
              <dt className="text-muted-foreground">Evidence</dt>
              <dd>{x.required_evidence}</dd>
              <dt className="text-muted-foreground">Source</dt>
              <dd className="font-mono text-xs">{x.source_reference}</dd>
            </dl>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => setSelected(x)}>
              {readOnly ? "View" : "Edit"}
            </Button>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">Effects: {Object.values(EFFECTS).join(" · ")}</p>
      {selected && <ExceptionEditor key={selected.id} rule={selected} versionId={version.id} readOnly={readOnly} onClose={() => setSelected(null)} />}
      {adding && <ExceptionEditor key="new" rule={null} versionId={version.id} readOnly={false} onClose={() => setAdding(false)} />}
    </div>
  );
}
