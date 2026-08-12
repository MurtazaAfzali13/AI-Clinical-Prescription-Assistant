"use client";

import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, PenLine, Sparkles, Stethoscope } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { VoiceRecorderButton } from "@/components/prescription/VoiceRecorderButton";
import { MedicationRowsEditor, emptyMedicationRows } from "@/components/prescription/MedicationRowsEditor";
import { ApiError, cdssApi, prescriptionApi } from "@/lib/api/client";
import type { Medication, PatientInfo, PrescriptionResponse } from "@/lib/types/prescription";
import type { CDSSPrescriptionResponse, CDSSReview } from "@/lib/types/cdss";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

interface PrescriptionFormProps {
  onResult: (result: PrescriptionResponse, patient: PatientInfo, cdssReview?: CDSSReview) => void;
}

interface StatusEvent {
  stage: string;
  label: string;
}

type Mode = "ai" | "manual";

/** Adapts the richer CDSS payload into the original PrescriptionResponse
 * shape so the existing preview/override/print flow keeps working
 * unchanged -- the full CDSSReview is passed through separately for the
 * additional Copilot Mode panels. */
function cdssResponseToLegacy(response: CDSSPrescriptionResponse): PrescriptionResponse {
  return {
    extraction: response.extraction!,
    warnings: response.review.safety_warnings.map((w) => ({
      medications: w.medications,
      severity: w.severity,
      explanation: w.explanation,
    })),
    is_safe: response.review.is_safe,
    trace_id: response.trace_id,
  };
}

export function PrescriptionForm({ onResult }: PrescriptionFormProps) {
  const [mode, setMode] = useState<Mode>("ai");
  const [copilotMode, setCopilotMode] = useState(false);
  const [patient, setPatient] = useState<PatientInfo>({ name: "", age: undefined, record_no: "" });
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // --- AI mode state ---
  const [rawText, setRawText] = useState("");
  const [statusEvents, setStatusEvents] = useState<StatusEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // --- Manual mode state ---
  const [diagnosis, setDiagnosis] = useState("");
  const [medications, setMedications] = useState<Medication[]>(emptyMedicationRows());

  function handleAiSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setStatusEvents([]);
    setIsRunning(true);

    eventSourceRef.current?.close();

    const endpoint = copilotMode ? "/cdss/prescriptions/stream" : "/prescriptions/stream";
    const params = new URLSearchParams({ raw_text: rawText });
    if (copilotMode) params.set("use_copilot_mode", "true");

    const source = new EventSource(`${API_BASE_URL}${endpoint}?${params.toString()}`);
    eventSourceRef.current = source;

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "status") {
        setStatusEvents((prev) => [...prev, { stage: data.stage, label: data.label }]);
      } else if (data.type === "result") {
        if (copilotMode) {
          const cdssResult = data.payload as CDSSPrescriptionResponse;
          cdssResult.extraction!.patient = { ...cdssResult.extraction!.patient, ...patient };
          onResult(cdssResponseToLegacy(cdssResult), patient, cdssResult.review);
        } else {
          const result = data.payload as PrescriptionResponse;
          // Overlay the patient fields the doctor typed in, since the stream
          // endpoint doesn't take structured patient input.
          result.extraction.patient = { ...result.extraction.patient, ...patient };
          onResult(result, patient);
        }
        source.close();
        setIsRunning(false);
      } else if (data.type === "error") {
        setError(data.message ?? "Something went wrong while processing this note.");
        source.close();
        setIsRunning(false);
      }
    };

    source.onerror = () => {
      setError("Lost connection to the agent pipeline. Please try again.");
      source.close();
      setIsRunning(false);
    };
  }

  async function handleManualSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const filledMedications = medications.filter((m) => m.name.trim() !== "");
    if (filledMedications.length === 0) {
      setError("Add at least one medication before running the safety check.");
      return;
    }

    setIsRunning(true);
    try {
      if (copilotMode) {
        const cdssResult = await cdssApi.createManual({
          patient,
          diagnosis,
          medications: filledMedications,
          use_copilot_mode: true,
        });
        onResult(cdssResponseToLegacy(cdssResult), patient, cdssResult.review);
      } else {
        const result = await prescriptionApi.createManual({
          patient,
          diagnosis,
          medications: filledMedications,
        });
        onResult(result, patient);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {mode === "ai" ? (
              <Sparkles className="h-4 w-4 text-clinic-600" />
            ) : (
              <PenLine className="h-4 w-4 text-clinic-600" />
            )}
            New prescription note
          </CardTitle>
          <div className="flex rounded-md border border-border bg-background/60 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setMode("ai")}
              className={`rounded px-2.5 py-1 transition-colors ${
                mode === "ai" ? "bg-clinic-800 text-white" : "text-ink/60 hover:text-ink"
              }`}
            >
              AI Dictation
            </button>
            <button
              type="button"
              onClick={() => setMode("manual")}
              className={`rounded px-2.5 py-1 transition-colors ${
                mode === "manual" ? "bg-clinic-800 text-white" : "text-ink/60 hover:text-ink"
              }`}
            >
              Write Manually
            </button>
          </div>
        </div>
        <p className="text-xs text-ink/60">
          {mode === "ai"
            ? "Write the patient encounter in plain English, or dictate it with the mic button. The Extractor agent will structure it, and the Safety agent will check for drug interactions before it reaches print."
            : "Enter the diagnosis and medications yourself -- the Extractor agent is skipped. The Safety agent still checks for drug interactions before printing."}
        </p>

        <div className="mt-1 flex items-center justify-between rounded-md border border-clinic-100 bg-clinic-50 px-3 py-2">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-clinic-700" />
            <div>
              <Label htmlFor="copilot-mode" className="text-xs font-medium text-clinic-800">
                Copilot Mode
              </Label>
              <p className="text-[11px] text-clinic-700/70">
                {copilotMode
                  ? mode === "ai"
                    ? "Full workup: Supervisor routes to Lab, Dose, Contraindication, and Guideline agents as needed."
                    : "Same Supervisor routing as AI dictation -- applies to your manually-entered diagnosis and medications too."
                  : mode === "ai"
                    ? "Fast mode: Extractor + Safety agent only (lower cost, lower latency)."
                    : "Fast mode: Safety agent only."}
              </p>
            </div>
          </div>
          <Switch id="copilot-mode" checked={copilotMode} onCheckedChange={setCopilotMode} />
        </div>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={mode === "ai" ? handleAiSubmit : handleManualSubmit}>
          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="patient-name">Patient name</Label>
              <Input
                id="patient-name"
                value={patient.name ?? ""}
                onChange={(e) => setPatient((p) => ({ ...p, name: e.target.value }))}
                placeholder="John Doe"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="patient-age">Age</Label>
              <Input
                id="patient-age"
                type="number"
                min={0}
                value={patient.age ?? ""}
                onChange={(e) =>
                  setPatient((p) => ({ ...p, age: e.target.value ? Number(e.target.value) : undefined }))
                }
                placeholder="34"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="record-no">Record no.</Label>
              <Input
                id="record-no"
                value={patient.record_no ?? ""}
                onChange={(e) => setPatient((p) => ({ ...p, record_no: e.target.value }))}
                placeholder="REC-0142"
              />
            </div>
          </div>

          {mode === "ai" ? (
            <>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="raw-text">Encounter note</Label>
                  <VoiceRecorderButton
                    onTranscript={(text) =>
                      setRawText((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text))
                    }
                  />
                </div>
                <Textarea
                  id="raw-text"
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Patient presents with fever and sore throat. Prescribe Acetaminophen 500mg twice a day for 5 days. Advise rest and fluids, follow up if fever persists."
                  required
                />
              </div>

              {statusEvents.length > 0 && (
                <div className="flex flex-col gap-1.5 rounded-md border border-clinic-100 bg-clinic-50 p-3">
                  {statusEvents.map((event, i) => {
                    const isLast = i === statusEvents.length - 1;
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs text-clinic-800">
                        {isLast && isRunning ? (
                          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-clinic-600" />
                        ) : (
                          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-clinic-600" />
                        )}
                        <span>{event.label}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="diagnosis">Diagnosis</Label>
                <Input
                  id="diagnosis"
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  placeholder="Essential hypertension"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Medications</Label>
                <MedicationRowsEditor medications={medications} onChange={setMedications} />
              </div>
            </>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-warn-red/30 bg-warn-red/5 p-3 text-sm text-warn-red">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button type="submit" disabled={isRunning} className="self-start">
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> {mode === "ai" ? "Analyzing..." : "Checking safety..."}
              </>
            ) : mode === "ai" ? (
              copilotMode ? "Run Copilot Workup" : "Run Extractor + Safety Check"
            ) : copilotMode ? (
              "Run Copilot Workup"
            ) : (
              "Run Safety Check"
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
