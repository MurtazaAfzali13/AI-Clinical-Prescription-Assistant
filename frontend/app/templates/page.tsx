import { ClipboardList } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { ComingSoon } from "@/components/layout/ComingSoon";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function TemplatesPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell doctorName={doctorName} doctorEmail={doctorEmail} title="Templates" subtitle="Reusable encounter note templates">
      <ComingSoon
        icon={ClipboardList}
        title="Note templates coming soon"
        description="Save common encounter note patterns (e.g. 'common cold', 'follow-up visit') to fill the form in one click."
      />
    </AppShell>
  );
}
