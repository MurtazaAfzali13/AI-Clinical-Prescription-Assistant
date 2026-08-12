import { Activity, BookOpen, FlaskConical, ShieldAlert, Shuffle } from "lucide-react";

import type { CDSSReview } from "@/lib/types/cdss";

function EvidenceTag({ source, confidence, guideline_section }: { source: string; confidence: number; guideline_section?: string | null }) {
  return (
    <span className="mt-1 inline-flex items-center gap-1 rounded-full border border-border bg-background/60 px-2 py-0.5 text-[10px] text-ink/50">
      {source}
      {guideline_section ? ` · ${guideline_section}` : ""} · {Math.round(confidence * 100)}% match
    </span>
  );
}

export function CDSSReviewPanel({ review }: { review: CDSSReview }) {
  const hasAnySpecialistData =
    review.dose_results.length > 0 ||
    review.contraindications.length > 0 ||
    review.guideline_recommendations.length > 0 ||
    review.alternative_therapies.length > 0 ||
    review.lab_context !== null;

  if (!hasAnySpecialistData) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4 rounded-md border border-clinic-100 bg-clinic-50/40 p-4">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-clinic-800">
        <Activity className="h-3.5 w-3.5" /> Copilot Mode findings
      </p>

      {review.lab_context && (
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-clinic-700">
            <FlaskConical className="h-3.5 w-3.5" /> Clinical context on file
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink/70">
            {review.lab_context.weight_kg != null && <span>Weight: {review.lab_context.weight_kg}kg</span>}
            {review.lab_context.egfr != null && <span>eGFR: {review.lab_context.egfr}</span>}
            {review.lab_context.liver_panel_normal != null && (
              <span>Liver panel: {review.lab_context.liver_panel_normal ? "normal" : "abnormal"}</span>
            )}
            {review.lab_context.chronic_conditions.length > 0 && (
              <span>Conditions: {review.lab_context.chronic_conditions.join(", ")}</span>
            )}
          </div>
        </div>
      )}

      {review.dose_results.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold text-clinic-700">Dose verification</p>
          <div className="flex flex-col gap-1.5">
            {review.dose_results.map((d, i) => (
              <div
                key={i}
                className={`rounded-md border px-3 py-2 text-xs ${
                  d.is_within_range === false
                    ? "border-warn-red/30 bg-warn-red/5 text-warn-red"
                    : "border-border bg-background/60 text-ink/70"
                }`}
              >
                <span className="font-medium">{d.medication_name}: </span>
                {d.explanation}
              </div>
            ))}
          </div>
        </div>
      )}

      {review.contraindications.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-clinic-700">
            <ShieldAlert className="h-3.5 w-3.5" /> Contraindications
          </p>
          <div className="flex flex-col gap-1.5">
            {review.contraindications.map((c, i) => (
              <div key={i} className="rounded-md border border-warn-red/30 bg-warn-red/5 px-3 py-2 text-xs text-warn-red">
                <p className="font-medium">
                  {c.medication_name} vs {c.condition} &mdash; {c.severity.toUpperCase()}
                </p>
                <p>{c.explanation}</p>
                {c.evidence && <EvidenceTag {...c.evidence} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {review.guideline_recommendations.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-clinic-700">
            <BookOpen className="h-3.5 w-3.5" /> Guideline recommendations
          </p>
          <div className="flex flex-col gap-1.5">
            {review.guideline_recommendations.map((g, i) => (
              <div key={i} className="rounded-md border border-border bg-background/60 px-3 py-2 text-xs text-ink/70">
                <p>{g.recommendation}</p>
                <EvidenceTag {...g.evidence} />
              </div>
            ))}
          </div>
        </div>
      )}

      {review.alternative_therapies.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-clinic-700">
            <Shuffle className="h-3.5 w-3.5" /> Suggested alternatives
          </p>
          <div className="flex flex-col gap-1.5">
            {review.alternative_therapies.map((a, i) => (
              <div key={i} className="rounded-md border border-clinic-200 bg-clinic-50 px-3 py-2 text-xs text-clinic-800">
                <p className="font-medium">
                  {a.original_medication} &rarr; {a.suggested_alternative}
                </p>
                <p className="text-clinic-700/80">{a.rationale}</p>
                {a.evidence && <EvidenceTag {...a.evidence} />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
