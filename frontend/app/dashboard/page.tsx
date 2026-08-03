import { AppShell } from "@/components/layout/AppShell";
import { DashboardClient } from "@/components/prescription/DashboardClient";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function DashboardPage() {
  const { doctorName, doctorEmail, isDemoMode } = await getDoctorSession();

  return (
    <AppShell
      doctorName={doctorName}
      doctorEmail={doctorEmail}
      title="New Prescription"
      subtitle={isDemoMode ? "Prescription desk · demo mode" : "Prescription desk"}
    >
      <DashboardClient doctorName={doctorName} />
    </AppShell>
  );
}
