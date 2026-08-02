import { redirect } from "next/navigation";
import dynamic from "next/dynamic";

import { createSupabaseServerClient } from "@/lib/supabase/server";

// recharts relies on ResizeObserver and other browser-only APIs; keep it
// out of the server-rendered / prerendered tree entirely.
const AnalyticsDashboard = dynamic(
  () => import("@/components/analytics/AnalyticsDashboard").then((m) => m.AnalyticsDashboard),
  { ssr: false }
);

const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export default async function AnalyticsPage() {
  let doctorName = "Dr. Demo";

  if (SUPABASE_CONFIGURED) {
    const supabase = createSupabaseServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      redirect("/login");
    }

    doctorName = (user.user_metadata?.full_name as string) ?? user.email ?? "Doctor";
  }

  return <AnalyticsDashboard doctorName={doctorName} />;
}
