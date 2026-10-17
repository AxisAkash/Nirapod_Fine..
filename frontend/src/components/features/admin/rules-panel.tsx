"use client";

import { useMemo, useState } from "react";

import { RuleEditor } from "@/components/features/admin/rule-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { compareSections, formatNumber } from "@/lib/format";
import type { AdminRule, AdminVersion } from "@/types/api";

export function RulesPanel({ version, rules }: { version: AdminVersion; rules: AdminRule[] }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<AdminRule | null>(null);
  const [adding, setAdding] = useState(false);
  const readOnly = version.status !== "draft";

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rules
      .filter((r) => !q || `${r.section_number} ${r.offence_title} ${r.offence_category ?? ""} ${r.aliases.map((a) => a.text).join(" ")}`.toLowerCase().includes(q))
      .sort((a, b) => compareSections(a.section_number, b.section_number));
  }, [rules, query]);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Viewing <b className="text-foreground">{version.version_name}</b>{" "}
          <span className={`rounded-full px-2 py-0.5 font-mono text-xs ${readOnly ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn"}`}>{readOnly ? "read-only" : "draft, editable"}</span>
        </p>
        <div className="flex gap-2">
          <Input aria-label="Search rules" className="w-64" placeholder="Search section, title or alias" value={query} onChange={(e) => setQuery(e.target.value)} />
          {!readOnly && <Button onClick={() => setAdding(true)}>Add rule</Button>}
        </div>
      </div>

      <div className="max-h-[34rem] overflow-auto rounded-xl border bg-card">
        <Table>
          <TableHeader className="sticky top-0 bg-card">
            <TableRow>
              <TableHead>Section</TableHead>
              <TableHead>Offence</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Max (Tk)</TableHead>
              <TableHead className="text-right">Aliases</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((r) => (
              <TableRow key={r.id} className="cursor-pointer" tabIndex={0} onClick={() => setSelected(r)} onKeyDown={(e) => e.key === "Enter" && setSelected(r)}>
                <TableCell className="font-mono">{r.section_number}</TableCell>
                <TableCell className="max-w-md">
                  {r.offence_title}
                  {!r.matchable && <span className="ml-2 rounded bg-muted px-1.5 py-0.5 font-mono text-[0.65rem] text-muted-foreground">supporting</span>}
                </TableCell>
                <TableCell className="text-muted-foreground">{r.offence_category}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{r.max_fine == null ? "none" : formatNumber(r.max_fine)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{r.aliases.length}</TableCell>
              </TableRow>
            ))}
            {shown.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                  No rules match your search.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {selected && <RuleEditor key={selected.id} rule={selected} versionId={version.id} readOnly={readOnly} open onClose={() => setSelected(null)} />}
      {adding && <RuleEditor key="new" rule={null} versionId={version.id} readOnly={false} open onClose={() => setAdding(false)} />}
    </div>
  );
}
