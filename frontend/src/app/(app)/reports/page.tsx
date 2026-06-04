"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Download, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { Card, PageHeader, Spinner, Badge } from "@/components/ui";
import type { Report } from "@/lib/types";

const STATUS_TONE: Record<string, string> = {
  done: "positive", failed: "negative", queued: "neutral", processing: "neutral",
};
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function ReportsPage() {
  const qc = useQueryClient();
  const [type, setType] = useState<"pdf" | "csv">("pdf");

  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: async () => (await api.get<{ reports: Report[]; total: number }>("/api/v1/reports?limit=20")).data.reports,
    refetchInterval: 5_000, // poll while jobs are processing
  });

  const create = useMutation({
    mutationFn: async () => api.post("/api/v1/reports", { type, filters: {} }),
    onSuccess: () => { toast.success("Report queued"); qc.invalidateQueries({ queryKey: ["reports"] }); },
    onError: () => toast.error("Could not queue report"),
  });

  function downloadHref(r: Report) {
    if (!r.download_url) return undefined;
    return r.download_url.startsWith("http") ? r.download_url : `${API_BASE}${r.download_url}`;
  }

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Generate and download PDF / CSV reports"
        actions={
          <div className="flex items-center gap-2">
            <select className="input" value={type} onChange={(e) => setType(e.target.value as "pdf" | "csv")}>
              <option value="pdf">PDF</option>
              <option value="csv">CSV</option>
            </select>
            <button className="btn-primary" disabled={create.isPending} onClick={() => create.mutate()}>
              <FileText size={16} /> Generate
            </button>
          </div>
        }
      />

      <Card>
        {reports.isLoading ? <Spinner /> : (
          <div className="divide-y divide-slate-200 dark:divide-slate-800">
            {(reports.data ?? []).map((r) => (
              <div key={r.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <FileText size={18} className="text-brand-500" />
                  <div>
                    <p className="text-sm font-medium uppercase">{r.type}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(r.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>
                  {r.status === "done" && downloadHref(r) && (
                    <a className="btn-ghost" href={downloadHref(r)} target="_blank" rel="noreferrer">
                      <Download size={16} /> Download
                    </a>
                  )}
                </div>
              </div>
            ))}
            {reports.data?.length === 0 && <p className="py-4 text-sm text-slate-500 dark:text-slate-400">No reports yet.</p>}
          </div>
        )}
      </Card>
    </div>
  );
}
