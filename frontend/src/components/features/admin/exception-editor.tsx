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

const dash = "\u2014";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-0.5 border-b py-2.5 last:border-b-0 sm:grid-cols-[10rem_1fr] sm:gap-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">{title}</h3>
      <dl className="rounded-lg border px-3">{children}</dl>
    </section>
  );
}

/** What an exception rule says, as plain text. Used for versions that are locked, so nothing looks editable. */
function ExceptionDetails({ rule, onClose }: { rule: AdminException; onClose: () => void }) {
  const appliesTo = rule.applies_to_section ? `Section ${rule.applies_to_section} only` : rule.applies_to_category === "*" || !rule.applies_to_category ? "Any offence" : `Offences in the “${rule.applies_to_category}” category`;
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{rule.exception_title}</DialogTitle>
          <DialogDescription>Part of a locked dataset version. To change it, create a draft on the Versions tab.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          {rule.exception_description && <p className="text-sm text-foreground/90">{rule.exception_description}</p>}
          <Group title="What it does">
            <Row label="Effect">{rule.effect ? EFFECTS[rule.effect] ?? rule.effect : dash}</Row>
            <Row label="Applies to">{appliesTo}</Row>
            <Row label="Vehicles">{rule.vehicle_types.length ? rule.vehicle_types.join(", ") : "Any vehicle"}</Row>
            {rule.conditions_text.length > 0 && (
              <Row label="Conditions">
                <ul className="list-disc pl-4">
                  {rule.conditions_text.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </Row>
            )}
          </Group>
          <Group title="Limits and evidence">
            <Row label="Scope limit">{rule.scope_limit || dash}</Row>
            <Row label="Evidence needed">{rule.required_evidence || dash}</Row>
            <Row label="Source">
              <span className="font-mono text-xs">{rule.source_reference || dash}</span>
            </Row>
          </Group>
          <Group title="How a claim is detected">
            <Row label="Claim words">
              {rule.keywords.length ? (
                <span className="flex flex-wrap gap-1.5">
                  {rule.keywords.map((k) => (
                    <span key={k.word} className="rounded-full bg-muted px-2.5 py-0.5 text-xs">
                      {k.word} <span className="text-muted-foreground">&times;{k.weight}</span>
                    </span>
                  ))}
                </span>
              ) : (
                dash
              )}
            </Row>
            <Row label="Internal key">
              <span className="font-mono text-xs">{rule.rule_key}</span>
            </Row>
          </Group>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

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

  if (readOnly && rule) return <ExceptionDetails rule={rule} onClose={onClose} />;

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{creating ? "Add an exception rule" : f.title}</DialogTitle>
          <DialogDescription>Every exception needs a scope limit. The engine will not apply it outside that scope.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-5">
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Basics</legend>
            <FormField label="Title" htmlFor="x-title" className="sm:col-span-2">
              <Input id="x-title" value={f.title} onChange={(e) => set("title", e.target.value)} />
            </FormField>
            <FormField label="Effect" htmlFor="x-effect" className="sm:col-span-2">
              <NativeSelect id="x-effect" value={f.effect} onChange={(e) => set("effect", e.target.value as typeof f.effect)}>
                {Object.entries(EFFECTS).map(([k, label]) => (
                  <option key={k} value={k}>
                    {label}
                  </option>
                ))}
              </NativeSelect>
            </FormField>
          </fieldset>

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-2 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">When it applies</legend>
            <FormField label="Section" htmlFor="x-section" hint="One section only, for example 66. Leave empty to use a category.">
              <Input id="x-section" value={f.section} onChange={(e) => set("section", e.target.value)} />
            </FormField>
            <FormField label="Category" htmlFor="x-category" hint="For example route_permit, or * for any offence">
              <Input id="x-category" value={f.category} onChange={(e) => set("category", e.target.value)} />
            </FormField>
            <FormField label="Vehicle types" htmlFor="x-vehicles" hint="Leave empty if any vehicle can use it" className="sm:col-span-2">
              <StringListEditor id="x-vehicles" items={f.vehicles} readOnly={false} onChange={(v) => set("vehicles", v)} placeholder="Add a vehicle and press Enter" />
            </FormField>
          </fieldset>

          <fieldset className="grid gap-3">
            <legend className="mb-2 font-mono text-xs font-medium tracking-wider text-muted-foreground uppercase">Limits and evidence</legend>
            <FormField label="Scope limit" htmlFor="x-scope" hint="What this exception does not cover">
              <Textarea id="x-scope" rows={2} value={f.scope} onChange={(e) => set("scope", e.target.value)} />
            </FormField>
            <FormField label="Evidence needed" htmlFor="x-evidence">
              <Input id="x-evidence" value={f.evidence} onChange={(e) => set("evidence", e.target.value)} />
            </FormField>
            <FormField label="Source" htmlFor="x-ref" hint="Where in the law this comes from">
              <Input id="x-ref" value={f.reference} onChange={(e) => set("reference", e.target.value)} />
            </FormField>
          </fieldset>

          <details open={creating} className="group rounded-lg border">
            <summary className="cursor-pointer px-3 py-2.5 text-sm font-medium select-none">Advanced</summary>
            <div className="grid gap-3 border-t p-3 sm:grid-cols-2">
              <FormField label="Key" htmlFor="x-key" hint="A short unique id, for example s30-emergency">
                <Input id="x-key" value={f.key} onChange={(e) => set("key", e.target.value)} />
              </FormField>
              <FormField label="Description" htmlFor="x-desc" className="sm:col-span-2">
                <Textarea id="x-desc" rows={3} value={f.description} onChange={(e) => set("description", e.target.value)} />
              </FormField>
              <FormField label="Conditions" htmlFor="x-cond" className="sm:col-span-2">
                <StringListEditor id="x-cond" items={f.conditions} readOnly={false} onChange={(v) => set("conditions", v)} placeholder="Add a condition and press Enter" />
              </FormField>
              <FormField label="Claim words (word and weight)" htmlFor="x-keywords" hint="Words in the receipt or notes that show this exception was claimed" className="sm:col-span-2">
                <KeywordEditor items={f.keywords} readOnly={false} onChange={(v) => set("keywords", v)} />
              </FormField>
            </div>
          </details>

          {error && (
            <p role="alert" className="text-sm text-bad">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          {!creating && (
            <Button variant="destructive" className="sm:mr-auto" disabled={busy} onClick={() => (confirmDelete ? void remove() : setConfirmDelete(true))}>
              {confirmDelete ? "Click again to delete" : "Delete exception"}
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={busy} onClick={save}>
            {busy ? "Saving…" : creating ? "Add exception" : "Save exception"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
