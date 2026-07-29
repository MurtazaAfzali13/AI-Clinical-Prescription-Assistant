import { redirect } from "next/navigation";

import { DashboardClient } from "@/components/prescription/DashboardClient";
import { createSupabaseServerClient } from "@/lib/supabase/server";

const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export default async function DashboardPage() {
  let doctorName = "Dr. Demo";
  let doctorEmail: string | null = null;

  if (SUPABASE_CONFIGURED) {
    const supabase = createSupabaseServerClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      redirect("/login");
    }

    doctorName = (user.user_metadata?.full_name as string) ?? user.email ?? "Doctor";
    doctorEmail = user.email ?? null;
  }

  return <DashboardClient doctorName={doctorName} doctorEmail={doctorEmail} isDemoMode={!SUPABASE_CONFIGURED} />;
}
