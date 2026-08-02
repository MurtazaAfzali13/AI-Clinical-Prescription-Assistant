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
