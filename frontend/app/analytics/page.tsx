import dynamic from "next/dynamic";

import { AppShell } from "@/components/layout/AppShell";
import { getDoctorSession } from "@/lib/auth/getDoctorSession";

// recharts relies on ResizeObserver and other browser-only APIs; keep it
// out of the server-rendered / prerendered tree entirely.
const AnalyticsDashboard = dynamic(
  () => import("@/components/analytics/AnalyticsDashboard").then((m) => m.AnalyticsDashboard),
  { ssr: false }
);

export default async function AnalyticsPage() {
  const { doctorName, doctorEmail } = await getDoctorSession();

  return (
    <AppShell doctorName={doctorName} doctorEmail={doctorEmail} title="Dashboard" subtitle="Today's vitals" bleed>
      <AnalyticsDashboard doctorName={doctorName} />
    </AppShell>
  );
}
