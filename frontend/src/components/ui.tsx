"use client";

import clsx from "clsx";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={clsx("card p-5", className)}>{children}</div>;
}

export function KpiCard({ label, value, hint, accent }: { label: string; value: string | number; hint?: string; accent?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span>
      <span className={clsx("text-3xl font-semibold", accent)}>{value}</span>
      {hint && <span className="text-xs text-slate-500 dark:text-slate-400">{hint}</span>}
    </Card>
  );
}

const SENTIMENT_STYLES: Record<string, string> = {
  positive: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  negative: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  neutral: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

export function Badge({ children, tone }: { children: React.ReactNode; tone?: string }) {
  return (
    <span className={clsx("inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
      SENTIMENT_STYLES[tone || ""] || "bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300")}>
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Spinner() {
  return <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />;
}
