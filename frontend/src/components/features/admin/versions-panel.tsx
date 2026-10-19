"use client";

import { Fragment, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, shortHash } from "@/lib/format";
import { cn } from "@/lib/utils";
import { activateVersion, anchorVersion, createDraft, getIntegrity, getVersionHash } from "@/services/admin.client";
import { integrityMeta } from "@/lib/audit";
import { TONE_STYLES } from "@/constants/status";
import type { AdminVersion, DatasetIntegrity } from "@/types/api";

const STATE_STYLE = { active: "bg-ok-bg text-ok", draft: "bg-warn-bg text-warn", archived: "bg-muted text-muted-foreground" };

export function VersionsPanel({ versions }: { versions: AdminVersion[] }) {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [activating, setActivating] = useState<AdminVersion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [hashes, setHashes] = useState<Record<string, string>>({});
  const [checks, setChecks] = useState<Record<string, DatasetIntegrity>>({});
  const [checking, setChecking] = useState<string | null>(null);
  const hasDraft = versions.some((v) => v.status === "draft");

  async function check(v: AdminVersion) {
    setChecking(v.id);
    try {
      const result = await getIntegrity(v.id);
      setChecks((s) => ({ ...s, [v.id]: result }));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not check the dataset.");
    } finally {
      setChecking(null);
    }
  }

  // The version in use is checked as soon as the page opens, so a changed rule is noticed straight away.
  const activeId = versions.find((v) => v.status === "active")?.id;
  useEffect(() => {
    if (!activeId) return;
    getIntegrity(activeId)
      .then((result) => setChecks((s) => ({ ...s, [activeId]: result })))
      .catch(() => undefined);
  }, [activeId]);

  async function run(task: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError(undefined);
    try {
      await task();
      toast.success(done);
      setCreating(false);
      setActivating(null);
      setName("");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          The active version is read-only so earlier audit hashes stay valid. Create a draft, edit it, then activate it. Cases already checked keep pointing at the version they used.
        </p>
        <Button disabled={hasDraft} onClick={() => setCreating(true)}>
          Create draft from active
        </Button>
      </div>
      {hasDraft && <p className="text-xs text-muted-foreground">One draft is already open. Activate it before creating another.</p>}

      <div className="overflow-hidden rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Version</TableHead>
              <TableHead>State</TableHead>
              <TableHead className="text-right">Offence rules</TableHead>
              <TableHead className="text-right">Exceptions</TableHead>
              <TableHead>Content hash</TableHead>
              <TableHead>Blockchain</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {versions.map((v) => (
              <Fragment key={v.id}>
              <TableRow>
                <TableCell>
                  <p className="font-medium">{v.version_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {v.description ?? ""} &middot; {formatDate(v.created_at)}
                  </p>
                </TableCell>
                <TableCell>
                  <span className={cn("rounded-full px-2.5 py-0.5 font-mono text-xs uppercase", STATE_STYLE[v.status])}>{v.status}</span>
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums">{v.offence_rule_count}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{v.exception_rule_count}</TableCell>
                <TableCell className="font-mono text-xs">
                  {hashes[v.id] ? (
                    <span title={hashes[v.id]}>{shortHash(hashes[v.id])}</span>
                  ) : (
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={async () => {
                        try {
                          const h = await getVersionHash(v.id);
                          setHashes((s) => ({ ...s, [v.id]: h.content_hash }));
                        } catch (e) {
                          toast.error(e instanceof Error ? e.message : "Could not read the hash.");
                        }
                      }}
                    >
                      Show
                    </Button>
                  )}
                </TableCell>
                <TableCell className="whitespace-normal">
                  {v.status === "draft" ? (
                    <span className="text-xs text-muted-foreground">Recorded when activated</span>
                  ) : (
                    <div className="grid gap-1">
                      <span className={cn("w-fit rounded-full px-2.5 py-0.5 font-mono text-xs", v.anchor_status === "anchored" ? "bg-ok-bg text-ok" : v.anchor_status === "pending" ? "bg-warn-bg text-warn" : "bg-muted text-muted-foreground")}>
                        {v.anchor_status === "anchored" ? "Recorded" : v.anchor_status === "pending" ? "Waiting" : "Not recorded"}
                      </span>
                      {checks[v.id] && (
                        <span className={cn("w-fit rounded-full px-2.5 py-0.5 font-mono text-xs", TONE_STYLES[integrityMeta(checks[v.id].status).tone].soft)}>
                          {integrityMeta(checks[v.id].status).label}
                        </span>
                      )}
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1.5">
                    <Link href={`/admin/dataset?tab=rules&version=${v.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
                      Open rules
                    </Link>
                    {v.status === "draft" && (
                      <Button size="sm" onClick={() => setActivating(v)}>
                        Activate
                      </Button>
                    )}
                    {v.status !== "draft" && (
                      <Button variant="outline" size="sm" disabled={checking === v.id} onClick={() => check(v)}>
                        {checking === v.id ? "Checking\u2026" : "Check integrity"}
                      </Button>
                    )}
                    {v.status !== "draft" && v.anchor_status !== "anchored" && (
                      <Button
                        size="sm"
                        onClick={async () => {
                          try {
                            await anchorVersion(v.id);
                            toast.success("Recorded on the blockchain.");
                            router.refresh();
                          } catch (e) {
                            toast.error(e instanceof Error ? e.message : "Could not record it.");
                          }
                        }}
                      >
                        Record on blockchain
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
              {checks[v.id] && checks[v.id].status !== "verified" && (
                <TableRow>
                  <TableCell colSpan={7} className={cn("whitespace-normal text-sm", TONE_STYLES[integrityMeta(checks[v.id].status).tone].soft)}>
                    <b>{integrityMeta(checks[v.id].status).label}.</b> {checks[v.id].message}
                    {checks[v.id].status === "tampered" && " New results are blocked until this is resolved."}
                  </TableCell>
                </TableRow>
              )}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create a draft version</DialogTitle>
            <DialogDescription>The draft starts as a copy of the active version. Nothing changes for users until you activate it.</DialogDescription>
          </DialogHeader>
          <FormField label="Version name" htmlFor="v-name" error={error} hint="For example v1.1 add Bangla aliases">
            <Input id="v-name" value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button disabled={busy || !name.trim()} onClick={() => run(() => createDraft(name.trim()), "Draft created.")}>
              {busy ? "Creating…" : "Create draft"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!activating} onOpenChange={(o) => !o && setActivating(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Activate {activating?.version_name}?</DialogTitle>
            <DialogDescription>
              New cases will be checked against this version. The current active version is archived and stays available to the cases that used it. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {error && (
            <p role="alert" className="text-sm text-bad">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setActivating(null)}>
              Cancel
            </Button>
            <Button disabled={busy} onClick={() => activating && run(() => activateVersion(activating.id), `${activating.version_name} is now active.`)}>
              {busy ? "Activating…" : "Activate version"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
