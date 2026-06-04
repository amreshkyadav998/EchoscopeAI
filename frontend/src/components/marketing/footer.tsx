"use client";

import Link from "next/link";
import { Github, Linkedin, Radar, Twitter } from "lucide-react";

const COLS = [
  { title: "Product", links: ["Features", "Analytics", "Alerts", "Reports", "Pricing"] },
  { title: "Resources", links: ["Documentation", "API Reference", "Guides", "Changelog"] },
  { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
  { title: "Legal", links: ["Privacy", "Terms", "Security", "Cookies"] },
];

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50">
      <div className="container-x py-14">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-6">
          <div className="col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white">
                <Radar size={18} />
              </span>
              <span className="text-lg font-bold">EchoscopeAI</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm text-slate-500 dark:text-slate-400">
              AI-powered social listening & reputation monitoring. Track every mention,
              understand sentiment, and act in real time.
            </p>
            <div className="mt-5 flex gap-3 text-slate-400">
              <a href="#" aria-label="Twitter" className="hover:text-brand-600"><Twitter size={18} /></a>
              <a href="#" aria-label="GitHub" className="hover:text-brand-600"><Github size={18} /></a>
              <a href="#" aria-label="LinkedIn" className="hover:text-brand-600"><Linkedin size={18} /></a>
            </div>
          </div>

          {COLS.map((c) => (
            <div key={c.title}>
              <h4 className="text-sm font-semibold">{c.title}</h4>
              <ul className="mt-4 space-y-2">
                {c.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="text-sm text-slate-500 transition hover:text-brand-600 dark:text-slate-400">{l}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-slate-200 pt-6 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400 sm:flex-row">
          <span>© {new Date().getFullYear()} EchoscopeAI. All rights reserved.</span>
          <span>Built with FastAPI · Kafka · Next.js</span>
        </div>
      </div>
    </footer>
  );
}
