"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { parseAmountInput } from "@/lib/format";
import { analyzeCase } from "@/services/cases.client";
import type { CaseExtracted, ManualFields } from "@/types/api";

/** Lets the user fix a misread field and run the analysis again on the same case. */
export function CorrectDetailsDialog({ caseId, extracted }: { caseId: string; extracted: CaseExtracted }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [v, setV] = useState({
    reason: extracted.reason ?? "",
    amount: extracted.amount != null ? String(extracted.amount) : "",
    section: extracted.section ?? "",
    vehicle: extracted.vehicle_type ?? "",
    date: extracted.date ?? "",
    location: extracted.location ?? "",
    receipt_number: extracted.receipt_number ?? "",
    notes: extracted.notes ?? "",
  });
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!v.reason.trim()) return setError("Enter the offence reason.");
    if (v.amount.trim() && parseAmountInput(v.amount) === undefined) return setError("The fine amount must be a number.");
    setBusy(true);
    setError(undefined);
    try {
      const fields: ManualFields = { ...v, amount: parseAmountInput(v.amount) };
      await analyzeCase(caseId, fields);
      toast.success("Analysed again with your corrections.");
      setOpen(false);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not re-run the analysis.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        Correct details
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Correct the receipt details</DialogTitle>
            <DialogDescription>If a field was read wrongly, fix it here. The case is analysed again and the result is replaced.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
            <FormField label="Offence reason" htmlFor="c-reason" className="sm:col-span-2">
              <Input id="c-reason" value={v.reason} onChange={set("reason")} />
            </FormField>
            <FormField label="Fine amount (Tk)" htmlFor="c-amount">
              <Input id="c-amount" inputMode="numeric" value={v.amount} onChange={set("amount")} />
            </FormField>
            <FormField label="Section cited" htmlFor="c-section" hint="For example 87, 89(1) or ধারা ৮৭">
              <Input id="c-section" value={v.section} onChange={set("section")} />
            </FormField>
            <FormField label="Vehicle type" htmlFor="c-vehicle">
              <Input id="c-vehicle" value={v.vehicle} onChange={set("vehicle")} />
            </FormField>
            <FormField label="Date" htmlFor="c-date">
              <Input id="c-date" type="date" value={v.date} onChange={set("date")} />
            </FormField>
            <FormField label="Location" htmlFor="c-location">
              <Input id="c-location" value={v.location} onChange={set("location")} />
            </FormField>
            <FormField label="Receipt number" htmlFor="c-number">
              <Input id="c-number" value={v.receipt_number} onChange={set("receipt_number")} />
            </FormField>
            <FormField label="Notes or claimed exception" htmlFor="c-notes" className="sm:col-span-2">
              <Textarea id="c-notes" rows={2} value={v.notes} onChange={set("notes")} />
            </FormField>
            {error && (
              <p role="alert" className="text-sm text-bad sm:col-span-2">
                {error}
              </p>
            )}
            <DialogFooter className="sm:col-span-2">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy}>
                {busy ? "Analysing…" : "Save and analyse again"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
