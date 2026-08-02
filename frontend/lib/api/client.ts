import type {
  PrescriptionRequest,
  PrescriptionResponse,
} from "@/lib/types/prescription";
import type { DashboardStats } from "@/lib/types/analytics";

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
  override: (payload: OverrideRequest) =>
    request<OverrideResponse>("/prescriptions/override", {
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
