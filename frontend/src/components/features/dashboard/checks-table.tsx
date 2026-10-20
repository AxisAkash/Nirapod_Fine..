import Link from "next/link";

import { NeutralPill, ResultPill } from "@/components/ui/result-pill";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { capitalize, shortUrl } from "@/lib/cases";
import { formatDateTime, formatNumber } from "@/lib/format";
import { safeHref } from "@/lib/validation";
import { cn } from "@/lib/utils";
import type { CaseListItem } from "@/types/api";

function SourceCell({ c }: { c: CaseListItem }) {
  if (c.case_source === "dummy_url") {
    const href = safeHref(c.dummy_url);
    return (
      <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
        <NeutralPill title="Illustrative sample data. Nothing was fetched from a URL.">Sample</NeutralPill>
        {c.dummy_url ? (
          href ? (
            <a href={href} target="_blank" rel="noopener noreferrer" title={c.dummy_url} className="text-primary hover:underline">
              {shortUrl(c.dummy_url)}
            </a>
          ) : (
            <span title={c.dummy_url} className="text-muted-foreground">{shortUrl(c.dummy_url)}</span>
          )
        ) : (
          <span className="text-muted-foreground">Illustrative notice</span>
        )}
      </span>
    );
  }
  return <span className="text-muted-foreground">{c.case_source === "receipt_upload" ? "Uploaded receipt" : "Typed details"}</span>;
}

const th = "font-mono text-[0.7rem] font-medium tracking-[0.06em] whitespace-nowrap text-muted-foreground uppercase";

/** The table of checks used on the Overview and Recent Checks pages. */
export function ChecksTable({ cases }: { cases: CaseListItem[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className={th}>Notice / Offence</TableHead>
          <TableHead className={cn(th, "hidden sm:table-cell")}>Source URL</TableHead>
          <TableHead className={th}>Section</TableHead>
          <TableHead className={cn(th, "text-right")}>Fine (Tk)</TableHead>
          <TableHead className={th}>Result</TableHead>
          <TableHead className={cn(th, "hidden sm:table-cell")}>Checked at</TableHead>
          <TableHead className={th}>Action</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {cases.map((c) => {
          const sub = [c.receipt_number, c.location].filter(Boolean).join(" · ");
          const name = capitalize(c.reason) || "Untitled case";
          return (
            <TableRow key={c.id}>
              <TableCell className="py-3.5 whitespace-normal">
                <b className="font-semibold">{name}</b>
                {sub && <div className="text-[0.78rem] text-muted-foreground">{sub}</div>}
              </TableCell>
              <TableCell className="hidden max-w-[260px] py-3.5 whitespace-normal sm:table-cell">
                <SourceCell c={c} />
              </TableCell>
              <TableCell className="py-3.5 font-mono">{c.section ?? "-"}</TableCell>
              <TableCell className="py-3.5 text-right font-mono tabular-nums">{c.amount != null ? formatNumber(c.amount) : "-"}</TableCell>
              <TableCell className="py-3.5">
                <ResultPill status={c.validation_status} />
              </TableCell>
              <TableCell className="hidden py-3.5 whitespace-nowrap sm:table-cell">{formatDateTime(c.created_at)}</TableCell>
              <TableCell className="py-3.5">
                <Link href={`/cases/${c.id}/result`} aria-label={`View details: ${name}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  View details
                </Link>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export function EmptyChecks({ showAction = true }: { showAction?: boolean }) {
  return (
    <div className="px-4 py-9 text-center text-muted-foreground">
      <b className="text-foreground">No checks yet</b>
      <p className={cn("mx-auto mt-1.5 max-w-[44ch]", showAction && "mb-3.5")}>Your analysed mamlas will appear here, with the offence, the matched section and the fine limit check.</p>
      {showAction && (
        <Link href="/dashboard#notice" className="inline-flex items-center rounded-md border border-lamp bg-lamp px-4 py-2 text-sm font-semibold text-[#0f2a20] hover:brightness-105">
          Analyze your first mamla
        </Link>
      )}
    </div>
  );
}
