import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

export interface DoctorSession {
  doctorName: string;
  doctorEmail: string | null;
  isDemoMode: boolean;
}

/**
 * Resolves the signed-in doctor for a Server Component page. Falls back to
 * a demo doctor when Supabase isn't configured, so the app stays usable
 * without a database. Redirects to /login if Supabase IS configured but no
 * session is present.
 */
export async function getDoctorSession(): Promise<DoctorSession> {
  if (!SUPABASE_CONFIGURED) {
    return { doctorName: "Dr. Demo", doctorEmail: null, isDemoMode: true };
  }

  const supabase = createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return {
    doctorName: (user.user_metadata?.full_name as string) ?? user.email ?? "Doctor",
    doctorEmail: user.email ?? null,
    isDemoMode: false,
  };
}
