"use client";

import { Bell, Search, Settings as SettingsIcon } from "lucide-react";

import { AppSidebar } from "@/components/layout/AppSidebar";
import { ThemeToggle } from "@/components/theme-toggle";

interface AppShellProps {
  doctorName: string;
  doctorEmail?: string | null;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  /** Render content edge-to-edge (no padding/max-width) -- used by the
   * analytics page, which manages its own dark "vitals" panel styling. */
  bleed?: boolean;
}

export function AppShell({ doctorName, doctorEmail, title, subtitle, children, bleed }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar doctorName={doctorName} doctorEmail={doctorEmail} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-border bg-card px-6 py-4">
          <div>
            <h1 className="font-display text-lg font-semibold text-ink">{title}</h1>
            {subtitle && <p className="text-xs text-ink/50">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-1.5">
            <button
              className="flex h-9 w-9 items-center justify-center rounded-md text-ink/50 hover:bg-clinic-800/5 hover:text-ink dark:hover:bg-white/5"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
            <button
              className="relative flex h-9 w-9 items-center justify-center rounded-md text-ink/50 hover:bg-clinic-800/5 hover:text-ink dark:hover:bg-white/5"
              aria-label="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-vitals-pulse" />
            </button>
            <button
              className="flex h-9 w-9 items-center justify-center rounded-md text-ink/50 hover:bg-clinic-800/5 hover:text-ink dark:hover:bg-white/5"
              aria-label="Settings"
            >
              <SettingsIcon className="h-4 w-4" />
            </button>
            <ThemeToggle />
          </div>
        </header>

        <main className={`flex-1 overflow-y-auto ${bleed ? "" : "px-6 py-6"}`}>{children}</main>
      </div>
    </div>
  );
}
