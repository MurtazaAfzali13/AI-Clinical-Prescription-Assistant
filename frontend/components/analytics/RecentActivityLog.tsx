import type { RecentPrescriptionSummary } from "@/lib/types/analytics";

function formatTime(iso: string): string {
  if (!iso) return "--:--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "--:--";
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

const STATUS_STYLES: Record<string, string> = {
  draft: "text-vitals-ink-muted",
  printed: "text-vitals-pulse",
  overridden: "text-vitals-warn",
};

export function RecentActivityLog({ items }: { items: RecentPrescriptionSummary[] }) {
  if (items.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-vitals-ink-muted">
        No activity recorded yet in this window.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-vitals-line">
      <table className="w-full font-mono text-xs">
        <thead>
          <tr className="border-b border-vitals-line bg-vitals-bg/40 text-left uppercase tracking-widest text-vitals-ink-muted">
            <th className="px-3 py-2 font-normal">Time</th>
            <th className="px-3 py-2 font-normal">Patient</th>
            <th className="px-3 py-2 font-normal">Diagnosis</th>
            <th className="px-3 py-2 font-normal text-right">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-vitals-line last:border-0">
              <td className="px-3 py-2 text-vitals-ink-muted">{formatTime(item.created_at)}</td>
              <td className="px-3 py-2 text-vitals-ink">{item.patient_name}</td>
              <td className="px-3 py-2 text-vitals-ink-muted">{item.diagnosis}</td>
              <td className={`px-3 py-2 text-right ${STATUS_STYLES[item.status] ?? "text-vitals-ink-muted"}`}>
                {item.is_safe ? item.status : `${item.status} \u26A0`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
