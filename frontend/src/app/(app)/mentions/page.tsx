"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, PageHeader, Spinner, Badge } from "@/components/ui";
import type { Mention } from "@/lib/types";

const SOURCES = ["", "mock", "reddit", "news", "rss", "blog"];

export default function MentionsPage() {
  const [source, setSource] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["mentions", source, page],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (source) params.set("source", source);
      return (await api.get<{ mentions: Mention[]; total: number; page: number }>(`/api/v1/mentions?${params}`)).data;
    },
  });

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / 20));

  return (
    <div>
      <PageHeader title="Mentions" subtitle={`${total} tracked mentions`} />

      <div className="mb-4 flex items-center gap-3">
        <select className="input max-w-xs" value={source} onChange={(e) => { setSource(e.target.value); setPage(1); }}>
          {SOURCES.map((s) => <option key={s} value={s}>{s ? s : "All sources"}</option>)}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Spinner /></div>
      ) : (
        <div className="space-y-3">
          {(data?.mentions ?? []).map((m) => (
            <Card key={m.id} className="!p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge>{m.source}</Badge>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(m.published_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-2 font-medium">{m.title || "(untitled)"}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">{m.content}</p>
                </div>
                <div className="shrink-0 text-right text-xs text-slate-500 dark:text-slate-400">
                  <div>▲ {m.upvotes}</div>
                  <div>💬 {m.comment_count}</div>
                </div>
              </div>
            </Card>
          ))}
          {total === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No mentions found.</p>}
        </div>
      )}

      {pages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <span className="text-sm">Page {page} / {pages}</span>
          <button className="btn-ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}
