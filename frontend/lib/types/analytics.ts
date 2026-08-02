export interface DailyCount {
  date: string;
  count: number;
}

export interface DiagnosisBreakdown {
  label: string;
  count: number;
}

export interface RecentPrescriptionSummary {
  patient_name: string;
  diagnosis: string;
  created_at: string;
  status: string;
  is_safe: boolean;
}

export interface DashboardStats {
  today_patients: number;
  today_prescriptions: number;
  active_patients: number;
  safety_warnings_today: number;
  daily_series: DailyCount[];
  top_diagnoses: DiagnosisBreakdown[];
  recent_prescriptions: RecentPrescriptionSummary[];
}
