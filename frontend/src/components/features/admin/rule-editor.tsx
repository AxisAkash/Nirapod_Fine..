"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { KeywordEditor, StringListEditor } from "@/components/features/admin/list-editors";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createRule, deleteRule, updateRule, type RuleInput } from "@/services/admin.client";
import type { AdminRule } from "@/types/api";

const isBangla = (s: string) => /[ঀ-৿]/.test(s);
const toNumber = (s: string): number | null => (s.trim() === "" ? null : Number(s.replace(/[^\d]/g, "")));

/** Create or edit an offence rule. Read-only when the version is not a draft. */
export function RuleEditor({
  rule,
  versionId,
  readOnly,
  open,
  onClose,
}: {
  rule: AdminRule | null;
  versionId: string;
  readOnly: boolean;
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const creating = rule === null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [f, setF] = useState(() => ({
    section: rule?.section_number ?? "",
    title: rule?.offence_title ?? "",
    category: rule?.offence_category ?? "",
    min: String(rule?.min_fine ?? 0),
    max: rule?.max_fine == null ? "" : String(rule.max_fine),
    fineText: rule?.fine_text ?? "",
    imprisonment: rule?.imprisonment_text ?? "",
    matchable: rule?.matchable ?? true,
    aliases: rule?.aliases.map((a) => a.text) ?? [],
    keywords: rule?.keywords ?? [],
  }));
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((s) => ({ ...s, [k]: v }));

  async function save() {
    if (!f.section.trim() || !f.title.trim()) return setError("Section number and title are required.");
    const body: RuleInput = {
      section_number: f.section.trim(),
      offence_title: f.title.trim(),
      offence_description: rule?.offence_description ?? f.title.trim(),
      offence_category: f.category.trim() || null,
      min_fine: toNumber(f.min) ?? 0,
      max_fine: toNumber(f.max),
      fine_text: f.fineText.trim() || null,
      imprisonment_text: f.imprisonment.trim() || null,
      repeat_rule_text: rule?.repeat_rule_text ?? null,
      source_reference: rule?.source_reference ?? null,
      matchable: f.matchable,
      fine_tiers: rule?.fine_tiers ?? [],
      aliases: f.aliases.map((text) => ({ text, language: isBangla(text) ? "bn" : "en" })),
      keywords: f.keywords,
    };
    setBusy(true);
    setError(undefined);
    try {
      if (creating) await createRule(versionId, body);
      else await updateRule(rule.id, body);
      toast.success(creating ? "Rule added to the draft." : "Rule saved in the draft.");
      onClose();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the rule.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!rule) return;
    setBusy(true);
    try {
      await deleteRule(rule.id);
      toast.success("Rule deleted from the draft.");
      onClose();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the rule.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{creating ? "Add an offence rule" : `Section ${rule.section_number}`}</DialogTitle>
          <DialogDescription>
            {readOnly ? "This version is not a draft, so it cannot be edited. Create a draft from the active version to make changes." : "Changes apply to this draft only until you activate it."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField label="Section number" htmlFor="r-section">
            <Input id="r-section" value={f.section} disabled={readOnly || !creating} onChange={(e) => set("section", e.target.value)} />
          </FormField>
          <FormField label="Category" htmlFor="r-category">
            <Input id="r-category" value={f.category} disabled={readOnly} onChange={(e) => set("category", e.target.value)} />
          </FormField>
          <FormField label="Title" htmlFor="r-title" className="sm:col-span-2">
            <Input id="r-title" value={f.title} disabled={readOnly} onChange={(e) => set("title", e.target.value)} />
          </FormField>
          <FormField label="Minimum fine (Tk)" htmlFor="r-min">
            <Input id="r-min" inputMode="numeric" value={f.min} disabled={readOnly} onChange={(e) => set("min", e.target.value)} />
          </FormField>
          <FormField label="Maximum fine (Tk)" htmlFor="r-max" hint="Leave empty if the law gives no Taka ceiling. Such cases go to manual review.">
            <Input id="r-max" inputMode="numeric" value={f.max} disabled={readOnly} onChange={(e) => set("max", e.target.value)} />
          </FormField>
          <FormField label="Fine as written in the law" htmlFor="r-fine-text" className="sm:col-span-2">
            <Input id="r-fine-text" value={f.fineText} disabled={readOnly} onChange={(e) => set("fineText", e.target.value)} />
          </FormField>
          <FormField label="Imprisonment" htmlFor="r-imp" className="sm:col-span-2">
            <Textarea id="r-imp" rows={2} value={f.imprisonment} disabled={readOnly} onChange={(e) => set("imprisonment", e.target.value)} />
          </FormField>
          {rule && rule.fine_tiers.length > 0 && (
            <div className="rounded-lg bg-muted p-3 text-sm sm:col-span-2">
              <p className="mb-1 font-medium">Fine tiers</p>
              {rule.fine_tiers.map((t) => (
                <p key={t.label} className="text-muted-foreground">
                  {t.label}: up to Tk {t.max_fine.toLocaleString("en-US")} (words: {t.keywords.join(", ")})
                </p>
              ))}
            </div>
          )}
          <FormField label="Aliases" htmlFor="r-alias" hint="Other ways a receipt may describe this offence, in English or Bangla" className="sm:col-span-2">
            <StringListEditor id="r-alias" items={f.aliases} readOnly={readOnly} onChange={(v) => set("aliases", v)} placeholder="Add an alias and press Enter" />
          </FormField>
          <FormField label="Keywords (word and weight)" htmlFor="r-keywords" hint="Higher weights count more toward matching" className="sm:col-span-2">
            <KeywordEditor items={f.keywords} readOnly={readOnly} onChange={(v) => set("keywords", v)} />
          </FormField>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={f.matchable} disabled={readOnly} onChange={(e) => set("matchable", e.target.checked)} className="size-4 accent-primary" />
            Can be selected automatically as the offence on a receipt
          </label>
          {error && (
            <p role="alert" className="text-sm text-bad sm:col-span-2">
              {error}
            </p>
          )}
        </div>
        <DialogFooter>
          {!readOnly && !creating && (
            <Button variant="destructive" className="sm:mr-auto" disabled={busy} onClick={() => (confirmDelete ? void remove() : setConfirmDelete(true))}>
              {confirmDelete ? "Click again to delete" : "Delete rule"}
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            {readOnly ? "Close" : "Cancel"}
          </Button>
          {!readOnly && (
            <Button disabled={busy} onClick={save}>
              {busy ? "Saving…" : creating ? "Add rule" : "Save rule"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
