"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ClipboardList,
  FileText,
  LayoutDashboard,
  LogOut,
  Pill,
  Settings as SettingsIcon,
  Users,
} from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/analytics", icon: LayoutDashboard },
  { label: "New Prescription", href: "/dashboard", icon: FileText },
  { label: "Patient Records", href: "/patients", icon: Users },
  { label: "Medications", href: "/medications", icon: Pill },
  { label: "Templates", href: "/templates", icon: ClipboardList },
  { label: "Settings", href: "/settings", icon: SettingsIcon },
];

const SUPABASE_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

interface AppSidebarProps {
  doctorName: string;
  doctorEmail?: string | null;
}

export function AppSidebar({ doctorName, doctorEmail }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const initials = doctorName
    .replace(/^Dr\.?\s*/i, "")
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  async function handleSignOut() {
    if (SUPABASE_CONFIGURED) {
      const supabase = createSupabaseBrowserClient();
      await supabase.auth.signOut();
    }
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-clinic-900 font-display text-sm text-white ring-2 ring-clinic-500/30">
          W
        </div>
        <div>
          <p className="font-display text-sm font-semibold leading-tight text-ink">Watan Hospital</p>
          <p className="text-[11px] leading-tight text-ink/50">Prescription System</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-clinic-800/10 text-clinic-800 dark:bg-vitals-pulse/10 dark:text-vitals-pulse"
                  : "text-ink/60 hover:bg-clinic-800/5 hover:text-ink dark:hover:bg-white/5"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-clinic-700 dark:bg-vitals-pulse" />
              )}
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <button
          onClick={handleSignOut}
          className="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-clinic-800/5 dark:hover:bg-white/5"
        >
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-clinic-100 font-mono text-xs font-semibold text-clinic-800 dark:bg-vitals-surface dark:text-vitals-pulse">
            {initials || "DR"}
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-card bg-vitals-pulse" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{doctorName}</p>
            <p className="truncate text-[11px] text-ink/50">{doctorEmail ?? "Prescription Desk"}</p>
          </div>
          <LogOut className="h-4 w-4 shrink-0 text-ink/40 group-hover:text-ink" />
        </button>
      </div>
    </aside>
  );
}
