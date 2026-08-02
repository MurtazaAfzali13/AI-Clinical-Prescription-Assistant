import Link from "next/link";
import { ArrowLeft, FileText } from "lucide-react";

import { PatientChatWidget } from "@/components/chat/PatientChatWidget";
import { ThemeToggle } from "@/components/theme-toggle";

export default function PatientsPage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-clinic-900 font-display text-white">
              W
            </div>
            <div>
              <p className="font-display text-xl font-semibold text-clinic-950">Watan Hospital</p>
              <p className="flex items-center gap-1 text-xs text-clinic-700">
                <FileText className="h-3 w-3" /> Patient Records
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-sm text-clinic-700 hover:text-clinic-900"
            >
              <ArrowLeft className="h-4 w-4" /> Back to prescriptions
            </Link>
            <ThemeToggle />
          </div>
        </header>

        <PatientChatWidget />
      </div>
    </main>
  );
}
