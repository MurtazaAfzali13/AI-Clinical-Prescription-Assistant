"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { DiagnosisBreakdown } from "@/lib/types/analytics";

const RING_COLORS = ["#35e0c0", "#1f8a76", "#7fa8a8", "#3a5a5f", "#254349"];

export function DiagnosesDonut({ data }: { data: DiagnosisBreakdown[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-vitals-ink-muted">
        No diagnoses recorded yet in this window.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="label"
              innerRadius={58}
              outerRadius={80}
              paddingAngle={2}
              stroke="#071a20"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={RING_COLORS[i % RING_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#0e2830",
                border: "1px solid #1c3a42",
                borderRadius: 8,
                fontSize: 12,
                fontFamily: "var(--font-mono)",
                color: "#eaf6f4",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-medium text-vitals-ink">{total}</span>
          <span className="text-[10px] uppercase tracking-widest text-vitals-ink-muted">total</span>
        </div>
      </div>
      <ul className="flex flex-col gap-1.5">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-2 text-vitals-ink-muted">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ backgroundColor: RING_COLORS[i % RING_COLORS.length] }}
              />
              {d.label}
            </span>
            <span className="font-mono tabular-nums text-vitals-ink">
              {d.count} &middot; {total > 0 ? Math.round((d.count / total) * 100) : 0}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
