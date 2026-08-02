"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface PulseStatProps {
  label: string;
  value: number;
  suffix?: string;
  trend?: number[];
  accent?: "pulse" | "warn";
}

export function PulseStat({ label, value, suffix, trend, accent = "pulse" }: PulseStatProps) {
  const color = accent === "warn" ? "#ff8a65" : "#35e0c0";
  const data = (trend && trend.length > 1 ? trend : [0, 0]).map((v, i) => ({ i, v }));

  return (
    <div className="relative overflow-hidden rounded-xl border border-vitals-line bg-vitals-surface p-4">
      <p className="text-[11px] uppercase tracking-widest text-vitals-ink-muted">{label}</p>
      <p className="mt-1 font-mono text-3xl font-medium tabular-nums text-vitals-ink">
        {value.toLocaleString()}
        {suffix && <span className="ml-1 text-sm text-vitals-ink-muted">{suffix}</span>}
      </p>
      {trend && (
        <div className="mt-2 h-8 w-full opacity-90">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`pulseFill-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#pulseFill-${label})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
