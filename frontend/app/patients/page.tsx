import { AppShell } from "@/components/layout/AppShell";
import { PatientChatWidget } from "@/components/chat/PatientChatWidget";
import { ReferPatientForm } from "@/components/chat/ReferPatientForm";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function PatientsPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell
      doctorName={doctorName}
      doctorEmail={doctorEmail}
      title="Patient Records"
      subtitle="Ask about a patient, or refer them to a colleague"
    >
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <PatientChatWidget />
        </div>
        <div>
          <ReferPatientForm />
        </div>
      </div>
    </AppShell>
  );
}
