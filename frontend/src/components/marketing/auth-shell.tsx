"use client";

import Link from "next/link";
import { ArrowLeft, CheckCircle2, Radar } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

const BULLETS = [
  "Track mentions across Reddit, news, RSS & blogs",
  "AI sentiment, spike detection & smart alerts",
  "Live dashboards updated in real time",
];

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Brand panel (hidden on small screens) */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-accent-700 p-12 text-white lg:flex">
        <div className="blob left-[-10%] top-[-10%] h-80 w-80 bg-white/30" />
        <div className="blob bottom-[-10%] right-[-5%] h-72 w-72 bg-accent-400/40" />

        <Link href="/" className="relative z-10 flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/15 backdrop-blur">
            <Radar size={20} />
          </span>
          <span className="text-xl font-bold">EchoscopeAI</span>
        </Link>

        <div className="relative z-10">
          <h2 className="text-3xl font-bold leading-snug">
            Protect your reputation,<br />before it’s a crisis.
          </h2>
          <ul className="mt-8 space-y-4">
            {BULLETS.map((b) => (
              <li key={b} className="flex items-center gap-3 text-white/90">
                <CheckCircle2 size={20} className="shrink-0 text-white" /> {b}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-sm text-white/70">
          “EchoscopeAI gives us a real-time pulse on how the world sees our brand.”
        </p>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col lg:w-1/2">
        <header className="flex items-center justify-between p-5">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-slate-500 transition hover:text-brand-600 dark:text-slate-400">
            <ArrowLeft size={16} /> Back to home
          </Link>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 items-center justify-center px-5 pb-12">
          <div className="w-full max-w-sm">
            {/* mobile logo */}
            <Link href="/" className="mb-8 flex items-center justify-center gap-2 lg:hidden">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white">
                <Radar size={20} />
              </span>
              <span className="text-xl font-bold">EchoscopeAI</span>
            </Link>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
