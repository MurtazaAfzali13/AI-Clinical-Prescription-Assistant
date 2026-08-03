import { Settings as SettingsIcon } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { ComingSoon } from "@/components/layout/ComingSoon";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

export default async function SettingsPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell doctorName={doctorName} doctorEmail={doctorEmail} title="Settings" subtitle="Profile & preferences">
      <ComingSoon
        icon={SettingsIcon}
        title="Profile settings coming soon"
        description="Manage your license number, specialty, signature, and notification preferences."
      />
    </AppShell>
  );
}
