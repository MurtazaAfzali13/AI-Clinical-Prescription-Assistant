"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { FileText, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PrescriptionForm } from "@/components/prescription/PrescriptionForm";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { PrescriptionResponse } from "@/lib/types/prescription";

// @react-pdf/renderer touches browser-only APIs; keep it out of the
// server-rendered / prerendered tree entirely.
const PrescriptionPreview = dynamic(
  () => import("@/components/prescription/PrescriptionPreview").then((m) => m.PrescriptionPreview),
  { ssr: false }
);

interface DashboardClientProps {
  doctorName: string;
  doctorEmail: string | null;
  isDemoMode: boolean;
}

export function DashboardClient({ doctorName, doctorEmail, isDemoMode }: DashboardClientProps) {
  const router = useRouter();
  const [result, setResult] = useState<PrescriptionResponse | null>(null);

  async function handleSignOut() {
    if (!isDemoMode) {
      const supabase = createSupabaseBrowserClient();
      await supabase.auth.signOut();
    }
    router.push("/login");
    router.refresh();
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-clinic-900 font-display text-white">
              W
            </div>
            <div>
              <p className="font-display text-xl font-semibold text-clinic-950">Watan Hospital</p>
              <p className="flex items-center gap-1 text-xs text-clinic-700">
                <FileText className="h-3 w-3" /> Prescription desk &middot; {doctorName}
                {doctorEmail ? ` (${doctorEmail})` : ""}
                {isDemoMode ? " · demo mode" : ""}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleSignOut}>
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <PrescriptionForm onResult={(res) => setResult(res)} />
          {result ? (
            <PrescriptionPreview result={result} doctorName={doctorName} />
          ) : (
            <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed border-clinic-200 text-sm text-ink/50">
              Run an encounter note to see the structured prescription here.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
