import type { InteractionWarning, PrescriptionExtraction, Severity } from "@/lib/types/prescription";

export interface EvidenceObject {
  source: string;
  url?: string | null;
  confidence: number;
  guideline_section?: string | null;
}

export interface RoutingDecision {
  run_dose_agent: boolean;
  run_lab_agent: boolean;
  run_contraindication_agent: boolean;
  run_guideline_agent: boolean;
  reasoning: string;
}

export interface LabContext {
  weight_kg?: number | null;
  age?: number | null;
  egfr?: number | null;
  liver_panel_normal?: boolean | null;
  labs_recorded_at?: string | null;
  chronic_conditions: string[];
  allergies: string[];
}

export interface DoseCheckResult {
  medication_name: string;
  prescribed_dose_mg?: number | null;
  recommended_min_mg?: number | null;
  recommended_max_mg?: number | null;
  is_within_range?: boolean | null;
  renal_adjustment_applied: boolean;
  explanation: string;
}

export interface ContraindicationWarning {
  medication_name: string;
  condition: string;
  severity: Severity;
  explanation: string;
  evidence?: EvidenceObject | null;
}

export interface GuidelineRecommendation {
  diagnosis: string;
  recommendation: string;
  evidence: EvidenceObject;
}

export interface AlternativeTherapy {
  original_medication: string;
  suggested_alternative: string;
  rationale: string;
  evidence?: EvidenceObject | null;
}

export interface EvidenceBackedWarning extends InteractionWarning {
  evidence?: EvidenceObject | null;
}

export interface CDSSReview {
  is_safe: boolean;
  overall_severity: Severity;
  summary: string;
  safety_warnings: EvidenceBackedWarning[];
  dose_results: DoseCheckResult[];
  contraindications: ContraindicationWarning[];
  guideline_recommendations: GuidelineRecommendation[];
  alternative_therapies: AlternativeTherapy[];
  lab_context?: LabContext | null;
  used_copilot_mode: boolean;
}

export interface CDSSPrescriptionResponse {
  review: CDSSReview;
  extraction?: PrescriptionExtraction | null;
  trace_id: string;
}
