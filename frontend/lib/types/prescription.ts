export type Severity = "none" | "low" | "moderate" | "high" | "critical";

export interface Medication {
  name: string;
  dosage: string;
  frequency: string;
  duration?: string | null;
}

export interface InteractionWarning {
  medications: string[];
  severity: Severity;
  explanation: string;
}

export interface PatientInfo {
  name?: string | null;
  age?: number | null;
  record_no?: string | null;
}

export interface PrescriptionExtraction {
  patient: PatientInfo;
  diagnosis: string;
  medications: Medication[];
  advice?: string | null;
}

export interface PrescriptionRequest {
  raw_text: string;
  patient: PatientInfo;
}

export interface PrescriptionResponse {
  extraction: PrescriptionExtraction;
  warnings: InteractionWarning[];
  is_safe: boolean;
  trace_id: string;
}

export interface PrintablePrescription {
  patient_name: string;
  age?: number | null;
  date: string; // ISO date
  record_no: string;
  diagnosis: string;
  advice: string;
  medications: Medication[];
  doctor_signature_name: string;
}
