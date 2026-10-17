import { apiFetch, jsonBody } from "@/services/client";
import type { CaseDetail, DummyScenario, ManualFields, UploadResult } from "@/types/api";

function appendFields(form: FormData, fields: ManualFields) {
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined && value !== "") form.append(key, String(value));
  }
}

export const uploadReceipt = (file: File, fields: ManualFields) => {
  const form = new FormData();
  form.append("file", file);
  appendFields(form, fields);
  return apiFetch<UploadResult>("/receipts/upload", { method: "POST", body: form });
};

export const createManualCase = (fields: ManualFields) =>
  apiFetch<CaseDetail>("/cases/manual", { method: "POST", ...jsonBody(fields) });

/** Runs the analysis. Optional fields correct the case first; calling it again replaces the earlier result. */
export const analyzeCase = (caseId: string, corrections?: ManualFields) =>
  apiFetch<CaseDetail>(`/cases/${caseId}/analyze`, { method: "POST", ...(corrections ? jsonBody(corrections) : {}) });

export const getScenarios = () => apiFetch<DummyScenario[]>("/dummy-url/scenarios");

/** Runs a sample notice through the analysis. The URL, if any, is kept on the case but never fetched. */
export const analyzeSample = (input: { url?: string; scenario?: string }) =>
  apiFetch<CaseDetail>("/dummy-url/analyze", { method: "POST", ...jsonBody(input) });
