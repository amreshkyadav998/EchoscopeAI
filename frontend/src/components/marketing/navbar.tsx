"use client";

import Link from "next/link";
import { Radar } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/store/auth";

const LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how", label: "How it works" },
  { href: "#analytics", label: "Analytics" },
  { href: "#faq", label: "FAQ" },
];

export function Navbar() {
  const token = useAuth((s) => s.accessToken);
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-950/70">
      <nav className="container-x flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white">
            <Radar size={18} />
          </span>
          <span className="text-lg font-bold tracking-tight">EchoscopeAI</span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="text-sm font-medium text-slate-600 transition hover:text-brand-600 dark:text-slate-300">
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {token ? (
            <Link href="/dashboard" className="btn-gradient">Open dashboard</Link>
          ) : (
            <>
              <Link href="/login" className="hidden btn-soft sm:inline-flex">Sign in</Link>
              <Link href="/register" className="btn-gradient">Get started</Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
