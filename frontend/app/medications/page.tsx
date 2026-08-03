import { Pill } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { ComingSoon } from "@/components/layout/ComingSoon";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function MedicationsPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell doctorName={doctorName} doctorEmail={doctorEmail} title="Medications" subtitle="Drug reference & inventory">
      <ComingSoon
        icon={Pill}
        title="Medications catalog coming soon"
        description="A searchable formulary with dosing guidance and the drug-interaction knowledge base used by the Safety agent."
      />
    </AppShell>
  );
}
