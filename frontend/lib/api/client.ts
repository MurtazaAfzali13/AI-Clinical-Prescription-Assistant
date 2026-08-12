import type {
  ManualPrescriptionRequest,
  PrescriptionRequest,
  PrescriptionResponse,
} from "@/lib/types/prescription";
import type { DashboardStats } from "@/lib/types/analytics";
import type { CDSSPrescriptionResponse } from "@/lib/types/cdss";

interface ReferPatientRequest {
  patient_record_no: string;
  to_doctor_email: string;
  reason?: string;
}

interface ReferPatientResponse {
  success: boolean;
  message: string;
}

interface OverrideRequest {
  trace_id: string;
  reason: string;
}

interface OverrideResponse {
  trace_id: string;
  status: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

interface ChatApiRequest {
  message: string;
  history: ChatTurn[];
}

interface ChatApiResponse {
  reply: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.message ?? "Request failed", response.status, body.error_code);
  }

  return response.json() as Promise<T>;
}

export const prescriptionApi = {
  create: (payload: PrescriptionRequest) =>
    request<PrescriptionResponse>("/prescriptions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createManual: (payload: ManualPrescriptionRequest) =>
    request<PrescriptionResponse>("/prescriptions/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  override: (payload: OverrideRequest) =>
    request<OverrideResponse>("/prescriptions/override", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const patientsApi = {
  refer: (payload: ReferPatientRequest) =>
    request<ReferPatientResponse>("/patients/refer", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const cdssApi = {
  // Manual entry, with the SAME Supervisor routing as AI dictation when
  // copilotMode is true -- fixes the gap where a manually-typed
  // prescription never reached the Supervisor at all.
  createManual: (payload: ManualPrescriptionRequest & { use_copilot_mode: boolean }) =>
    request<CDSSPrescriptionResponse>("/cdss/prescriptions/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const chatApi = {
  sendMessage: (payload: ChatApiRequest) =>
    request<ChatApiResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const analyticsApi = {
  getDashboard: () => request<DashboardStats>("/analytics/dashboard"),
};

export const transcriptionApi = {
  transcribe: async (audioBlob: Blob): Promise<{ text: string }> => {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");

    // Deliberately bypass the shared `request()` helper: it always sets
    // Content-Type: application/json, but a multipart upload needs the
    // browser to set its own Content-Type with the correct boundary.
    const response = await fetch(`${API_BASE_URL}/transcribe`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(body.message ?? "Transcription failed", response.status, body.error_code);
    }

    return response.json();
  },
};
