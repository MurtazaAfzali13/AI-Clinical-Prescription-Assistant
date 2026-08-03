import { AppShell } from "@/components/layout/AppShell";
import { PatientChatWidget } from "@/components/chat/PatientChatWidget";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function PatientsPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell
      doctorName={doctorName}
      doctorEmail={doctorEmail}
      title="Patient Records"
      subtitle="Ask about a patient or refer them to a colleague"
    >
      <div className="mx-auto max-w-3xl">
        <PatientChatWidget />
      </div>
    </AppShell>
  );
}
