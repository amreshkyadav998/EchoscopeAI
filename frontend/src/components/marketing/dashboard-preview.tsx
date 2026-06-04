"use client";

import { Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

const AREA = [
  { v: 12 }, { v: 18 }, { v: 15 }, { v: 26 }, { v: 22 }, { v: 34 },
  { v: 30 }, { v: 45 }, { v: 38 }, { v: 52 }, { v: 60 }, { v: 78 },
];
const DONUT = [
  { name: "Positive", value: 62, color: "#10b981" },
  { name: "Negative", value: 21, color: "#ef4444" },
  { name: "Neutral", value: 17, color: "#94a3b8" },
];

export function DashboardPreview() {
  return (
    <div className="relative rounded-2xl border border-slate-200 bg-white shadow-glow dark:border-slate-800 dark:bg-slate-900">
      {/* faux window chrome */}
      <div className="flex items-center gap-1.5 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <span className="h-3 w-3 rounded-full bg-red-400" />
        <span className="h-3 w-3 rounded-full bg-amber-400" />
        <span className="h-3 w-3 rounded-full bg-emerald-400" />
        <span className="ml-3 text-xs text-slate-400">app.echoscope.ai/dashboard</span>
      </div>

      <div className="space-y-4 p-5">
        {/* KPI tiles */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Mentions", value: "12,480", tone: "text-brand-600" },
            { label: "Positive", value: "62%", tone: "text-emerald-500" },
            { label: "Alerts", value: "7", tone: "text-accent-600" },
          ].map((k) => (
            <div key={k.label} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
              <p className="text-[11px] uppercase tracking-wide text-slate-400">{k.label}</p>
              <p className={`text-xl font-bold ${k.tone}`}>{k.value}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* area chart */}
          <div className="col-span-2 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
            <p className="mb-1 text-xs font-medium text-slate-500">Mention volume</p>
            <ResponsiveContainer width="100%" height={130}>
              <AreaChart data={AREA}>
                <defs>
                  <linearGradient id="pv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="v" stroke="#6366f1" strokeWidth={2} fill="url(#pv)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {/* donut */}
          <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
            <p className="mb-1 text-xs font-medium text-slate-500">Sentiment</p>
            <ResponsiveContainer width="100%" height={130}>
              <PieChart>
                <Pie data={DONUT} dataKey="value" innerRadius={28} outerRadius={50} paddingAngle={3}>
                  {DONUT.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
