"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { KeywordEditor, StringListEditor } from "@/components/features/admin/list-editors";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { createException, deleteException, updateException, type ExceptionInput } from "@/services/admin.client";
import type { AdminException } from "@/types/api";

export const EFFECTS: Record<string, string> = {
  exempts: "Exempts: a real exemption when in scope",
  permission_based: "Permission based: needs prior permission or evidence",
  no_general_exemption: "No general exemption: a claim the law does not accept",
  repealed: "Repealed: not current law",
};

export function ExceptionEditor({
  rule,
  versionId,
  readOnly,
  onClose,
}: {
  rule: AdminException | null;
  versionId: string;
  readOnly: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const creating = rule === null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [f, setF] = useState(() => ({
    key: rule?.rule_key ?? "",
    title: rule?.exception_title ?? "",
    description: rule?.exception_description ?? "",
    section: rule?.applies_to_section ?? "",
    category: rule?.applies_to_category ?? "",
    effect: rule?.effect ?? "exempts",
    vehicles: rule?.vehicle_types ?? [],
    conditions: rule?.conditions_text ?? [],
    scope: rule?.scope_limit ?? "",
    evidence: rule?.required_evidence ?? "",
    reference: rule?.source_reference ?? "",
    keywords: rule?.keywords ?? [],
  }));
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((s) => ({ ...s, [k]: v }));

  async function save() {
    if (!f.key.trim() || !f.title.trim()) return setError("A key and a title are required.");
    const body: ExceptionInput = {
      rule_key: f.key.trim(),
      exception_title: f.title.trim(),
      exception_description: f.description.trim(),
      applies_to_section: f.section.trim() || null,
      applies_to_category: f.category.trim() || null,
      effect: f.effect,
      vehicle_types: f.vehicles,
      conditions_text: f.conditions,
      scope_limit: f.scope.trim() || null,
      required_evidence: f.evidence.trim() || null,
      source_reference: f.reference.trim() || null,
      keywords: f.keywords,
    };
    setBusy(true);
    setError(undefined);
    try {
      if (creating) await createException(versionId, body);
      else await updateException(rule.id, body);
      toast.success(creating ? "Exception added to the draft." : "Exception saved in the draft.");
      onClose();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the exception.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!rule) return;
    setBusy(true);
    try {
      await deleteException(rule.id);
      toast.success("Exception deleted from the draft.");
      onClose();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the exception.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{creating ? "Add an exception rule" : f.title}</DialogTitle>
          <DialogDescription>{readOnly ? "This version is not a draft, so it cannot be edited." : "Every exception needs a scope limit. The engine will not apply it outside that scope."}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField label="Key" htmlFor="x-key" hint="A short unique id, for example s30-emergency">
            <Input id="x-key" value={f.key} disabled={readOnly} onChange={(e) => set("key", e.target.value)} />
          </FormField>
          <FormField label="Effect" htmlFor="x-effect">
            <NativeSelect id="x-effect" value={f.effect} disabled={readOnly} onChange={(e) => set("effect", e.target.value as typeof f.effect)}>
              {Object.entries(EFFECTS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </NativeSelect>
          </FormField>
          <FormField label="Title" htmlFor="x-title" className="sm:col-span-2">
            <Input id="x-title" value={f.title} disabled={readOnly} onChange={(e) => set("title", e.target.value)} />
          </FormField>
          <FormField label="Description" htmlFor="x-desc" className="sm:col-span-2">
            <Textarea id="x-desc" rows={3} value={f.description} disabled={readOnly} onChange={(e) => set("description", e.target.value)} />
          </FormField>
          <FormField label="Applies to section" htmlFor="x-section" hint="For one section only, for example 66">
            <Input id="x-section" value={f.section} disabled={readOnly} onChange={(e) => set("section", e.target.value)} />
          </FormField>
          <FormField label="Applies to category" htmlFor="x-category" hint="For example route_permit, or * for any offence">
            <Input id="x-category" value={f.category} disabled={readOnly} onChange={(e) => set("category", e.target.value)} />
          </FormField>
          <FormField label="Scope limit" htmlFor="x-scope" className="sm:col-span-2">
            <Textarea id="x-scope" rows={2} value={f.scope} disabled={readOnly} onChange={(e) => set("scope", e.target.value)} />
          </FormField>
          <FormField label="Required evidence" htmlFor="x-evidence" className="sm:col-span-2">
            <Input id="x-evidence" value={f.evidence} disabled={readOnly} onChange={(e) => set("evidence", e.target.value)} />
          </FormField>
          <FormField label="Source" htmlFor="x-ref" className="sm:col-span-2">
            <Input id="x-ref" value={f.reference} disabled={readOnly} onChange={(e) => set("reference", e.target.value)} />
          </FormField>
          <FormField label="Vehicle types" htmlFor="x-vehicles" hint="Vehicles this exemption covers" className="sm:col-span-2">
            <StringListEditor id="x-vehicles" items={f.vehicles} readOnly={readOnly} onChange={(v) => set("vehicles", v)} placeholder="Add a vehicle and press Enter" />
          </FormField>
          <FormField label="Conditions" htmlFor="x-cond" className="sm:col-span-2">
            <StringListEditor id="x-cond" items={f.conditions} readOnly={readOnly} onChange={(v) => set("conditions", v)} placeholder="Add a condition and press Enter" />
          </FormField>
          <FormField label="Claim keywords (word and weight)" htmlFor="x-keywords" hint="Words in the receipt or notes that show this exception was claimed" className="sm:col-span-2">
            <KeywordEditor items={f.keywords} readOnly={readOnly} onChange={(v) => set("keywords", v)} />
          </FormField>
          {error && (
            <p role="alert" className="text-sm text-bad sm:col-span-2">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          {!readOnly && !creating && (
            <Button variant="destructive" className="sm:mr-auto" disabled={busy} onClick={() => (confirmDelete ? void remove() : setConfirmDelete(true))}>
              {confirmDelete ? "Click again to delete" : "Delete exception"}
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            {readOnly ? "Close" : "Cancel"}
          </Button>
          {!readOnly && (
            <Button disabled={busy} onClick={save}>
              {busy ? "Saving…" : creating ? "Add exception" : "Save exception"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
