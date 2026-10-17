/** Shapes returned by the FastAPI backend. Kept in step with backend/app/schemas.py and serializers. */

export type ValidationStatus =
  | "VALID"
  | "INVALID_FINE_TOO_HIGH"
  | "INVALID_REASON_MISMATCH"
  | "VALID_BUT_EXCEPTION_POSSIBLE"
  | "INVALID_EXCEPTION_NOT_APPLICABLE"
  | "NEEDS_MANUAL_REVIEW"
  | "PENDING_ANALYSIS";

export interface Me {
  id: string;
  email: string | null;
  full_name: string | null;
  role: "user" | "admin";
}

export interface CaseListItem {
  id: string;
  created_at: string;
  case_source: string;
  validation_status: ValidationStatus;
  reason: string | null;
  amount: number | null;
  section: string | null;
  confidence: number | null;
  receipt_number: string | null;
  location: string | null;
  dummy_url: string | null;
}

export interface CaseList {
  items: CaseListItem[];
  total: number;
}

export interface AnalysisCandidate {
  section: string;
  title: string;
  category: string;
  reason_score: number;
  section_score: number;
  amount_score: number;
  total: number;
  why: string[];
}

export interface AnalysisException {
  key: string;
  title: string;
  effect: string;
  source_reference: string;
  scope_limit: string;
  required_evidence: string;
  claimed: boolean;
  applies: boolean;
  informational: boolean;
  reason: string;
}

export interface Justification {
  tone: "ok" | "bad" | "warn" | "info";
  title: string;
  text: string;
  meta: string;
  /** "exception" lines are shown under the exception checks, everything else under "Checks performed". */
  kind: "check" | "exception";
}

export interface Analysis {
  status: ValidationStatus;
  summary: string;
  confidence: number;
  matched_section: string | null;
  matched_title: string | null;
  matched_category: string | null;
  cited_section: string | null;
  cited_rule_section: string | null;
  statutory_max: number | null;
  statutory_min: number | null;
  fine_text: string | null;
  tier: string | null;
  allowed_fine: number | null;
  previous_fine: number | null;
  occurrence: number;
  flags: string[];
  manual_reason: string | null;
  dataset: string;
  candidates: AnalysisCandidate[];
  exceptions: AnalysisException[];
  justifications: Justification[];
}

export interface CaseExtracted {
  reason: string | null;
  amount: number | null;
  date: string | null;
  location: string | null;
  vehicle_type: string | null;
  receipt_number: string | null;
  section: string | null;
  notes: string | null;
}

export interface CaseDetail {
  id: string;
  created_at: string;
  updated_at: string;
  case_source: string;
  dummy_url: string | null;
  validation_status: ValidationStatus;
  validation_summary: string | null;
  ai_explanation: string | null;
  confidence_score: number | null;
  extracted: CaseExtracted;
  manual_input: Record<string, string | number | null>;
  receipt: { id: string; file_name: string | null; file_type: string | null; file_hash: string | null } | null;
  dataset: { id: string; name: string } | null;
  matched_rule: {
    id: string;
    section: string;
    title: string;
    category: string | null;
    min_fine: number;
    max_fine: number | null;
    fine_text: string | null;
    imprisonment_text: string | null;
    source_reference: string | null;
  } | null;
  matches: { section: string; title: string; score: number; reason: string | null }[];
  exception_checks: { key: string; title: string; applies: boolean; reason: string | null; source_reference: string | null }[];
  analysis: Analysis | null;
}

export interface UploadResult {
  receipt_id: string;
  case_id: string;
  file_name: string | null;
  file_type: string;
  file_hash: string;
}

/** Receipt fields the user can type or correct. */
export interface ManualFields {
  reason?: string;
  amount?: string | number;
  section?: string;
  vehicle?: string;
  notes?: string;
  date?: string;
  location?: string;
  receipt_number?: string;
}

export interface DummyScenario {
  key: string;
  reason: string;
  amount: number;
  vehicle: string;
  section: string;
  location: string;
  date: string;
  notes: string;
  receipt_number: string;
}

export interface DummyPreview {
  reason: string;
  amount: number;
  vehicle: string;
  section: string;
  location: string;
  date: string;
  notes: string;
  receipt_number: string;
}

// ---- admin ----------------------------------------------------------------------------------------
export interface AdminVersion {
  id: string;
  version_name: string;
  description: string | null;
  status: "draft" | "active" | "archived";
  is_active: boolean;
  source_file_name: string | null;
  source_hash: string;
  created_at: string;
  offence_rule_count: number;
  exception_rule_count: number;
}

export interface AliasItem {
  text: string;
  language: string;
}
export interface KeywordItem {
  word: string;
  weight: number;
}
export interface FineTier {
  label: string;
  max_fine: number;
  keywords: string[];
}

export interface AdminRule {
  id: string;
  dataset_version_id: string;
  section_number: string;
  offence_title: string;
  offence_description: string | null;
  offence_category: string | null;
  min_fine: number;
  max_fine: number | null;
  fine_text: string | null;
  imprisonment_text: string | null;
  repeat_rule_text: string | null;
  source_reference: string | null;
  matchable: boolean;
  fine_tiers: FineTier[];
  aliases: AliasItem[];
  keywords: KeywordItem[];
}

export type ExceptionEffect = "exempts" | "permission_based" | "no_general_exemption" | "repealed";

export interface AdminException {
  id: string;
  dataset_version_id: string;
  rule_key: string;
  exception_title: string;
  exception_description: string;
  applies_to_section: string | null;
  applies_to_category: string | null;
  effect: ExceptionEffect | null;
  vehicle_types: string[];
  conditions_text: string[];
  scope_limit: string | null;
  required_evidence: string | null;
  source_reference: string | null;
  keywords: KeywordItem[];
}

export interface PublicRule {
  id: string;
  section_number: string;
  offence_title: string;
  category: string | null;
  min_fine: number;
  max_fine: number | null;
  fine_text: string | null;
  imprisonment_text: string | null;
  matchable: boolean;
  fine_tiers: FineTier[];
}
