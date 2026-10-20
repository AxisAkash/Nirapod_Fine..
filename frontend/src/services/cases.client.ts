import { apiFetch, jsonBody } from "@/services/client";
import type { AuditSummary, CaseDetail, DummyScenario, UploadResult, VerifyResult } from "@/types/api";

/** Uploads a file. The service reads it with AI and returns what it found. Nothing can be typed in alongside it. */
export const uploadReceipt = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UploadResult>("/receipts/upload", { method: "POST", body: form });
};

/** Runs the analysis on the case as stored; calling it again replaces the earlier result. */
export const analyzeCase = (caseId: string) => apiFetch<CaseDetail>(`/cases/${caseId}/analyze`, { method: "POST" });

export const getScenarios = () => apiFetch<DummyScenario[]>("/dummy-url/scenarios");

/** Runs a sample notice through the analysis. The URL, if any, is kept on the case but never fetched. */
export const analyzeSample = (input: { url?: string; scenario?: string }) =>
  apiFetch<CaseDetail>("/dummy-url/analyze", { method: "POST", ...jsonBody(input) });

/** Recomputes the case, dataset and result fingerprints and compares them with the blockchain. */
export const verifyCase = (caseId: string) => apiFetch<VerifyResult>(`/cases/${caseId}/verify`);

/** Records a case on the blockchain, or retries a pending or failed record. */
export const recordCase = (caseId: string) => apiFetch<AuditSummary>("/blockchain/record", { method: "POST", ...jsonBody({ case_id: caseId }) });
