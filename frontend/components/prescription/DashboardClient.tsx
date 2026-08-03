"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

import { PrescriptionForm } from "@/components/prescription/PrescriptionForm";
import type { PrescriptionResponse } from "@/lib/types/prescription";

// @react-pdf/renderer touches browser-only APIs; keep it out of the
// server-rendered / prerendered tree entirely.
const PrescriptionPreview = dynamic(
  () => import("@/components/prescription/PrescriptionPreview").then((m) => m.PrescriptionPreview),
  { ssr: false }
);

interface DashboardClientProps {
  doctorName: string;
}

export function DashboardClient({ doctorName }: DashboardClientProps) {
  const [result, setResult] = useState<PrescriptionResponse | null>(null);

  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 lg:grid-cols-2">
      <PrescriptionForm onResult={(res) => setResult(res)} />
      {result ? (
        <PrescriptionPreview result={result} doctorName={doctorName} />
      ) : (
        <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-border text-sm text-ink/50">
          Run an encounter note to see the structured prescription here.
        </div>
      )}
    </div>
  );
}
