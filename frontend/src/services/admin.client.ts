import { apiFetch, jsonBody } from "@/services/client";
import type { AdminException, AdminRule, AdminVersion, AliasItem, FineTier, KeywordItem } from "@/types/api";

export const createDraft = (name: string, description?: string) =>
  apiFetch<AdminVersion>("/admin/dataset-versions", { method: "POST", ...jsonBody({ name, description }) });

export const activateVersion = (id: string) =>
  apiFetch<AdminVersion>(`/admin/dataset-versions/${id}/activate`, { method: "POST" });

export const getVersionHash = (id: string) =>
  apiFetch<{ version_id: string; source_hash: string; content_hash: string }>(`/admin/dataset-versions/${id}/hash`);

export interface RuleInput {
  section_number: string;
  offence_title: string;
  offence_description?: string | null;
  offence_category?: string | null;
  min_fine: number;
  max_fine: number | null;
  fine_text?: string | null;
  imprisonment_text?: string | null;
  repeat_rule_text?: string | null;
  source_reference?: string | null;
  matchable: boolean;
  fine_tiers: FineTier[];
  aliases: AliasItem[];
  keywords: KeywordItem[];
}

export const createRule = (versionId: string, rule: RuleInput) =>
  apiFetch<AdminRule>("/admin/offence-rules", { method: "POST", ...jsonBody({ ...rule, dataset_version_id: versionId }) });
export const updateRule = (id: string, rule: RuleInput) =>
  apiFetch<AdminRule>(`/admin/offence-rules/${id}`, { method: "PUT", ...jsonBody(rule) });
export const deleteRule = (id: string) => apiFetch<void>(`/admin/offence-rules/${id}`, { method: "DELETE" });

export interface ExceptionInput {
  rule_key: string;
  exception_title: string;
  exception_description: string;
  applies_to_section: string | null;
  applies_to_category: string | null;
  effect: string;
  vehicle_types: string[];
  conditions_text: string[];
  scope_limit: string | null;
  required_evidence: string | null;
  source_reference: string | null;
  keywords: KeywordItem[];
}

export const createException = (versionId: string, rule: ExceptionInput) =>
  apiFetch<AdminException>("/admin/exception-rules", { method: "POST", ...jsonBody({ ...rule, dataset_version_id: versionId }) });
export const updateException = (id: string, rule: ExceptionInput) =>
  apiFetch<AdminException>(`/admin/exception-rules/${id}`, { method: "PUT", ...jsonBody(rule) });
export const deleteException = (id: string) => apiFetch<void>(`/admin/exception-rules/${id}`, { method: "DELETE" });
