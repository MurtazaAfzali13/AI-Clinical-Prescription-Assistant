"use client";

import { useMemo, useState } from "react";
import { pdf } from "@react-pdf/renderer";
import { AlertOctagon, CheckCircle2, Printer, ShieldAlert, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { CDSSReviewPanel } from "@/components/prescription/CDSSReviewPanel";
import { ApiError, prescriptionApi } from "@/lib/api/client";
import { PrescriptionPDF } from "@/lib/pdf/PrescriptionPDF";
import type { PrescriptionResponse, Severity } from "@/lib/types/prescription";
import type { CDSSReview } from "@/lib/types/cdss";

interface PrescriptionPreviewProps {
  result: PrescriptionResponse;
  doctorName: string;
  cdssReview?: CDSSReview;
}

const SEVERITY_STYLES: Record<Severity, string> = {
  none: "bg-clinic-50 text-clinic-800 border-clinic-200",
  low: "bg-clinic-50 text-clinic-800 border-clinic-200",
  moderate: "bg-warn-amber/10 text-warn-amber border-warn-amber/30",
  high: "bg-warn-red/10 text-warn-red border-warn-red/30",
  critical: "bg-warn-red/15 text-warn-red border-warn-red/40",
};

export function PrescriptionPreview({ result, doctorName, cdssReview }: PrescriptionPreviewProps) {
  const { extraction, warnings, is_safe: baseIsSafe, trace_id: traceId } = result;

  const [isPreparingPrint, setIsPreparingPrint] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [isOverriding, setIsOverriding] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [wasOverridden, setWasOverridden] = useState(false);

  const isSafe = baseIsSafe || wasOverridden;

  const printable = useMemo(
    () => ({
      patient_name: extraction.patient.name || "—",
      age: extraction.patient.age,
      date: new Date().toISOString().slice(0, 10),
      record_no: extraction.patient.record_no || traceId.slice(0, 8).toUpperCase(),
      diagnosis: extraction.diagnosis,
      advice: extraction.advice ?? "",
      medications: extraction.medications,
      doctor_signature_name: doctorName,
    }),
    [extraction, traceId, doctorName]
  );

  async function handlePrint() {
    setIsPreparingPrint(true);
    try {
      const blob = await pdf(<PrescriptionPDF data={printable} />).toBlob();
      const url = URL.createObjectURL(blob);
      const printWindow = window.open(url, "_blank");
      printWindow?.addEventListener("load", () => printWindow.print());
    } finally {
      setIsPreparingPrint(false);
    }
  }

  async function handleOverride() {
    setOverrideError(null);
    if (overrideReason.trim().length < 5) {
      setOverrideError("Please document a clinical justification (at least a few words).");
      return;
    }

    setIsOverriding(true);
    try {
      await prescriptionApi.override({ trace_id: traceId, reason: overrideReason.trim() });
      setWasOverridden(true);
    } catch (err) {
      setOverrideError(err instanceof ApiError ? err.message : "Could not record the override. Please try again.");
    } finally {
      setIsOverriding(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          Review before print
          {cdssReview?.used_copilot_mode && (
            <span className="rounded-full bg-clinic-800/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-clinic-800">
              Copilot Mode
            </span>
          )}
        </CardTitle>
        {isSafe ? (
          <span className="flex items-center gap-1 rounded-full border border-clinic-200 bg-clinic-50 px-2.5 py-1 text-xs font-medium text-clinic-800">
            {wasOverridden ? (
              <ShieldCheck className="h-3.5 w-3.5" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5" />
            )}
            {wasOverridden ? "Overridden by physician" : "Safe to print"}
          </span>
        ) : (
          <span className="flex items-center gap-1 rounded-full border border-warn-red/30 bg-warn-red/10 px-2.5 py-1 text-xs font-medium text-warn-red">
            <AlertOctagon className="h-3.5 w-3.5" /> Review required
          </span>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-clinic-700">Diagnosis</p>
          <p className="text-sm text-ink">{extraction.diagnosis}</p>
        </div>

        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-clinic-700">Medications</p>
          <div className="overflow-hidden rounded-md border border-border">
            <table className="w-full text-sm">
              <thead className="bg-clinic-50 text-xs text-clinic-800">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Name</th>
                  <th className="px-3 py-2 text-left font-medium">Dosage</th>
                  <th className="px-3 py-2 text-left font-medium">Frequency</th>
                  <th className="px-3 py-2 text-left font-medium">Duration</th>
                </tr>
              </thead>
              <tbody>
                {extraction.medications.map((med, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{med.name}</td>
                    <td className="px-3 py-2 text-ink/70">{med.dosage}</td>
                    <td className="px-3 py-2 text-ink/70">{med.frequency}</td>
                    <td className="px-3 py-2 text-ink/70">{med.duration ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {extraction.advice && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clinic-700">Advice / Treatment</p>
            <p className="text-sm text-ink">{extraction.advice}</p>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-warn-red">
              <ShieldAlert className="h-3.5 w-3.5" /> Interaction warnings
            </p>
            {warnings.map((warning, i) => (
              <div key={i} className={`rounded-md border px-3 py-2 text-sm ${SEVERITY_STYLES[warning.severity]}`}>
                <p className="font-medium">
                  {warning.medications.join(" + ")} &mdash; {warning.severity.toUpperCase()}
                </p>
                <p className="text-xs opacity-90">{warning.explanation}</p>
              </div>
            ))}
          </div>
        )}

        {cdssReview && <CDSSReviewPanel review={cdssReview} />}

        {!baseIsSafe && !wasOverridden && (
          <div className="flex flex-col gap-2 rounded-md border border-warn-red/20 bg-warn-red/5 p-3">
            <p className="text-xs font-semibold text-warn-red">
              Human-in-the-loop: attending physician override
            </p>
            <p className="text-xs text-ink/70">
              Printing is blocked because the Safety agent flagged a high-severity interaction. If you&apos;ve
              reviewed this clinically and want to proceed anyway, document why below.
            </p>
            <Textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. Benefit outweighs risk given short treatment course; patient will be monitored for bleeding signs."
              className="min-h-[70px] text-sm"
            />
            {overrideError && <p className="text-xs text-warn-red">{overrideError}</p>}
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleOverride}
              disabled={isOverriding}
              className="self-start"
            >
              {isOverriding ? "Recording override..." : "Override and allow printing"}
            </Button>
          </div>
        )}

        <Button onClick={handlePrint} disabled={!isSafe || isPreparingPrint} className="self-start">
          <Printer className="h-4 w-4" />
          {isPreparingPrint ? "Preparing..." : "Print prescription"}
        </Button>
      </CardContent>
    </Card>
  );
}
