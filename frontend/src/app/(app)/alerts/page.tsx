"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, PageHeader, Spinner, Badge } from "@/components/ui";
import type { AlertItem, AlertRule } from "@/lib/types";

export default function AlertsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState("volume");
  const [threshold, setThreshold] = useState(50);

  const rules = useQuery({
    queryKey: ["rules"],
    queryFn: async () => (await api.get<{ rules: AlertRule[] }>("/api/v1/alerts/rules")).data.rules,
  });
  const history = useQuery({
    queryKey: ["alert-history"],
    queryFn: async () => (await api.get<{ alerts: AlertItem[] }>("/api/v1/alerts/history?limit=20")).data.alerts,
  });

  const createRule = useMutation({
    mutationFn: async () =>
      api.post("/api/v1/alerts/rules", {
        name, condition: { type, threshold }, channels: ["websocket", "email"],
      }),
    onSuccess: () => { toast.success("Rule created"); setName(""); qc.invalidateQueries({ queryKey: ["rules"] }); },
    onError: () => toast.error("Could not create rule"),
  });

  const deleteRule = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/v1/alerts/rules/${id}`),
    onSuccess: () => { toast.success("Rule deleted"); qc.invalidateQueries({ queryKey: ["rules"] }); },
  });

  return (
    <div>
      <PageHeader title="Alerts" subtitle="Rules & triggered alert history" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h3 className="mb-4 font-semibold">Create rule</h3>
          <form
            className="space-y-3"
            onSubmit={(e) => { e.preventDefault(); createRule.mutate(); }}
          >
            <input className="input" placeholder="Rule name" required value={name} onChange={(e) => setName(e.target.value)} />
            <div className="flex gap-3">
              <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="volume">Volume ≥</option>
                <option value="negative_pct">Negative % ≥</option>
                <option value="spike">Spike detected</option>
              </select>
              <input className="input" type="number" step="any" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
            </div>
            <button className="btn-primary w-full" disabled={createRule.isPending}>Add rule</button>
          </form>

          <div className="mt-6 space-y-2">
            {rules.isLoading ? <Spinner /> : (rules.data ?? []).map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div>
                  <p className="text-sm font-medium">{r.name}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {String(r.condition.type)} · {r.channels.join(", ")}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={r.is_enabled ? "positive" : "neutral"}>{r.is_enabled ? "on" : "off"}</Badge>
                  <button className="btn-ghost !px-2" onClick={() => deleteRule.mutate(r.id)}><Trash2 size={16} /></button>
                </div>
              </div>
            ))}
            {rules.data?.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No rules yet.</p>}
          </div>
        </Card>

        <Card>
          <h3 className="mb-4 font-semibold">Alert history</h3>
          <div className="space-y-2">
            {history.isLoading ? <Spinner /> : (history.data ?? []).map((a) => (
              <div key={a.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{a.keyword}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{new Date(a.triggered_at).toLocaleString()}</span>
                </div>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{a.trigger_reason}</p>
              </div>
            ))}
            {history.data?.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No alerts triggered yet.</p>}
          </div>
        </Card>
      </div>
    </div>
  );
}
