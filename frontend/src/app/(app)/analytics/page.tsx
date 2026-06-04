"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { Card, PageHeader, Spinner } from "@/components/ui";
import type { KeywordStat, SentimentBreakdown, SourceStat, TrendPoint } from "@/lib/types";

const TABS = ["Trends", "Sentiment", "Keywords", "Sources"] as const;
const COLORS = ["#10b981", "#ef4444", "#94a3b8"];

export default function AnalyticsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Trends");

  const trends = useQuery({
    queryKey: ["trends"],
    queryFn: async () => (await api.get<{ datapoints: TrendPoint[] }>("/api/v1/analytics/trends?granularity=day")).data.datapoints,
    enabled: tab === "Trends",
  });
  const sentiment = useQuery({
    queryKey: ["sentiment-page"],
    queryFn: async () => (await api.get<SentimentBreakdown>("/api/v1/analytics/sentiment")).data,
    enabled: tab === "Sentiment",
  });
  const keywords = useQuery({
    queryKey: ["top-keywords"],
    queryFn: async () => (await api.get<{ keywords: KeywordStat[] }>("/api/v1/analytics/keywords/top?limit=10")).data.keywords,
    enabled: tab === "Keywords",
  });
  const sources = useQuery({
    queryKey: ["sources"],
    queryFn: async () => (await api.get<{ sources: SourceStat[] }>("/api/v1/analytics/sources")).data.sources,
    enabled: tab === "Sources",
  });

  const sd = sentiment.data;
  const pie = sd ? [
    { name: "Positive", value: sd.positive }, { name: "Negative", value: sd.negative }, { name: "Neutral", value: sd.neutral },
  ] : [];

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Trends, sentiment, keywords & sources" />

      <div className="mb-6 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={t === tab ? "btn-primary" : "btn-ghost"}
          >
            {t}
          </button>
        ))}
      </div>

      <Card>
        {tab === "Trends" && (
          trends.isLoading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={trends.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:opacity-20" />
                <XAxis dataKey="time" hide />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="positive" stroke="#10b981" dot={false} />
                <Line type="monotone" dataKey="negative" stroke="#ef4444" dot={false} />
                <Line type="monotone" dataKey="neutral" stroke="#94a3b8" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )
        )}

        {tab === "Sentiment" && (
          sentiment.isLoading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={340}>
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={120} label>
                  {pie.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )
        )}

        {tab === "Keywords" && (
          keywords.isLoading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={keywords.data ?? []} layout="vertical" margin={{ left: 40 }}>
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis type="category" dataKey="word" width={100} stroke="#94a3b8" fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )
        )}

        {tab === "Sources" && (
          sources.isLoading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={sources.data ?? []}>
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )
        )}
      </Card>
    </div>
  );
}
