"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { PulseStat } from "@/components/analytics/PulseStat";
import { VolumeTraceChart } from "@/components/analytics/VolumeTraceChart";
import { DiagnosesDonut } from "@/components/analytics/DiagnosesDonut";
import { RecentActivityLog } from "@/components/analytics/RecentActivityLog";
import { ApiError, analyticsApi } from "@/lib/api/client";
import type { DashboardStats } from "@/lib/types/analytics";

interface AnalyticsDashboardProps {
  doctorName: string;
}

export function AnalyticsDashboard({ doctorName }: AnalyticsDashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    analyticsApi
      .getDashboard()
      .then((result) => {
        if (!cancelled) setStats(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load dashboard data.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="min-h-full bg-vitals-bg px-6 py-8 text-vitals-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-vitals-pulse opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-vitals-pulse" />
          </span>
          <p className="font-mono text-[11px] uppercase tracking-widest text-vitals-ink-muted">
            Live &middot; {today} &middot; {doctorName}
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-vitals-warn/30 bg-vitals-warn/10 px-3 py-2 text-sm text-vitals-warn">
            <AlertTriangle className="h-4 w-4" /> {error}
          </div>
        )}

        {!stats && !error && (
          <div className="flex h-64 items-center justify-center gap-2 text-sm text-vitals-ink-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Reading today&rsquo;s vitals...
          </div>
        )}

        {stats && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <PulseStat
                label="Patients today"
                value={stats.today_patients}
                trend={stats.daily_series.slice(-7).map((d) => d.count)}
              />
              <PulseStat
                label="Prescriptions today"
                value={stats.today_prescriptions}
                trend={stats.daily_series.slice(-7).map((d) => d.count)}
              />
              <PulseStat label="Active patients" value={stats.active_patients} />
              <PulseStat
                label="Safety flags today"
                value={stats.safety_warnings_today}
                accent={stats.safety_warnings_today > 0 ? "warn" : "pulse"}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="rounded-xl border border-vitals-line bg-vitals-surface p-5 lg:col-span-2">
                <p className="mb-1 text-[11px] uppercase tracking-widest text-vitals-ink-muted">
                  Prescription volume, last 14 days
                </p>
                <VolumeTraceChart data={stats.daily_series} />
              </div>
              <div className="rounded-xl border border-vitals-line bg-vitals-surface p-5">
                <p className="mb-3 text-[11px] uppercase tracking-widest text-vitals-ink-muted">
                  Diagnoses mix
                </p>
                <DiagnosesDonut data={stats.top_diagnoses} />
              </div>
            </div>

            <div className="rounded-xl border border-vitals-line bg-vitals-surface p-5">
              <p className="mb-3 text-[11px] uppercase tracking-widest text-vitals-ink-muted">
                Recent activity
              </p>
              <RecentActivityLog items={stats.recent_prescriptions} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
