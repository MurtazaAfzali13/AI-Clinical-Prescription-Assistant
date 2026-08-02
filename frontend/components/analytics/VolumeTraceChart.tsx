"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { DailyCount } from "@/lib/types/analytics";

function formatDayLabel(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

export function VolumeTraceChart({ data }: { data: DailyCount[] }) {
  const chartData = data.map((d) => ({ label: formatDayLabel(d.date), count: d.count }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#35e0c0" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#35e0c0" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1c3a42" strokeDasharray="0" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#7fa8a8"
            tick={{ fill: "#7fa8a8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "#1c3a42" }}
          />
          <YAxis
            stroke="#7fa8a8"
            tick={{ fill: "#7fa8a8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              background: "#0e2830",
              border: "1px solid #1c3a42",
              borderRadius: 8,
              fontSize: 12,
              fontFamily: "var(--font-mono)",
              color: "#eaf6f4",
            }}
            labelStyle={{ color: "#7fa8a8" }}
            cursor={{ stroke: "#35e0c0", strokeWidth: 1, strokeDasharray: "3 3" }}
          />
          <Area
            type="monotone"
            dataKey="count"
            name="Prescriptions"
            stroke="#35e0c0"
            strokeWidth={2}
            fill="url(#volumeFill)"
            dot={false}
            activeDot={{ r: 4, fill: "#35e0c0", stroke: "#071a20", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
