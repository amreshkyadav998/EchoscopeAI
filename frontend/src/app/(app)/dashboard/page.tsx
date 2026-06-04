"use client";

import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { KpiCard, Card, PageHeader, Spinner, Badge } from "@/components/ui";
import { useDashboardSocket } from "@/hooks/useDashboardSocket";
import type { Overview, SentimentBreakdown, AlertItem } from "@/lib/types";

export default function DashboardPage() {
  const live = useDashboardSocket();

  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: async () => (await api.get<Overview>("/api/v1/analytics/overview")).data,
    refetchInterval: 30_000,
  });
  const sentiment = useQuery({
    queryKey: ["sentiment"],
    queryFn: async () => (await api.get<SentimentBreakdown>("/api/v1/analytics/sentiment")).data,
    refetchInterval: 30_000,
  });
  const alerts = useQuery({
    queryKey: ["recent-alerts"],
    queryFn: async () => (await api.get<{ alerts: AlertItem[] }>("/api/v1/alerts/history?limit=8")).data.alerts,
  });

  const ov = overview.data;
  const timeline = sentiment.data?.timeline ?? [];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Live overview of your brand mentions"
        actions={live.connected ? <Badge tone="positive">● Live</Badge> : <Badge tone="neutral">offline</Badge>}
      />

      {overview.isLoading ? (
        <div className="flex justify-center py-20"><Spinner /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Total mentions" value={ov?.total_mentions ?? 0} />
            <KpiCard label="Positive" value={`${Math.round((ov?.positive_pct ?? 0) * 100)}%`} accent="text-emerald-500" />
            <KpiCard label="Negative" value={`${Math.round((ov?.negative_pct ?? 0) * 100)}%`} accent="text-rose-500" />
            <KpiCard label="Avg / day" value={ov?.avg_per_day ?? 0} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <h3 className="mb-4 font-semibold">Mention volume</h3>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" hide />
                  <YAxis width={30} stroke="#94a3b8" fontSize={12} />
                  <Tooltip />
                  <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="url(#g)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card>
              <h3 className="mb-4 font-semibold">Recent alerts</h3>
              <div className="space-y-3">
                {(alerts.data ?? []).length === 0 && (
                  <p className="text-sm text-slate-500 dark:text-slate-400">No alerts yet.</p>
                )}
                {(alerts.data ?? []).map((a) => (
                  <div key={a.id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{a.keyword}</span>
                      <Badge tone="negative">{a.channel}</Badge>
                    </div>
                    <p className="mt-1 text-slate-500 dark:text-slate-400">{a.trigger_reason}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
