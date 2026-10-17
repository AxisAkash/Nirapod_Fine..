import "server-only";
import { cache } from "react";

import { ApiError } from "@/services/api-error";
import { backendGet } from "@/services/backend.server";
import type {
  AdminException,
  AdminRule,
  AdminVersion,
  CaseDetail,
  CaseList,
  Me,
  PublicRule,
} from "@/types/api";

/** Cached per request, so the layout and a page can both ask without two round trips. */
export const getMe = cache(() => backendGet<Me>("/me"));

export function listCases(params: { status?: string; limit?: number; offset?: number } = {}) {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  q.set("limit", String(params.limit ?? 200));
  if (params.offset) q.set("offset", String(params.offset));
  return backendGet<CaseList>(`/cases?${q}`);
}

/** Returns null when the case does not exist or belongs to someone else. */
export async function getCase(id: string): Promise<CaseDetail | null> {
  try {
    return await backendGet<CaseDetail>(`/cases/${encodeURIComponent(id)}`);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 422)) return null;
    throw e;
  }
}

export const getPublicRules = () => backendGet<{ dataset: { id: string; name: string }; items: PublicRule[] }>("/offence-rules");

export const getAdminVersions = () => backendGet<AdminVersion[]>("/admin/dataset-versions");
export const getAdminRules = (versionId: string) => backendGet<AdminRule[]>(`/admin/offence-rules?version_id=${versionId}`);
export const getAdminExceptions = (versionId: string) =>
  backendGet<AdminException[]>(`/admin/exception-rules?version_id=${versionId}`);
