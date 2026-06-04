import Link from "next/link";
import {
  ArrowRight, BarChart3, Bell, Brain, CheckCircle2, FileText, Globe,
  MessagesSquare, Radar, Sparkles, TrendingUp, Users, Zap,
} from "lucide-react";
import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";
import { DashboardPreview } from "@/components/marketing/dashboard-preview";

const FEATURES = [
  { icon: MessagesSquare, title: "Mention tracking", desc: "Track brands, products & people across Reddit, news, RSS and blogs — deduplicated in real time." },
  { icon: Brain, title: "AI sentiment", desc: "Positive / negative / neutral with confidence scores, NER and keyword extraction on every mention." },
  { icon: TrendingUp, title: "Spike detection", desc: "Z-score anomaly detection on mention volume catches reputation events before they blow up." },
  { icon: BarChart3, title: "Live dashboards", desc: "Beautiful charts for trends, sentiment, top keywords and sources — updated over WebSockets." },
  { icon: Bell, title: "Smart alerts", desc: "Rule-based alerts via email & WebSocket with debouncing, so you’re notified — never spammed." },
  { icon: FileText, title: "PDF / CSV reports", desc: "On-demand and scheduled reports with embedded charts, delivered to secure storage." },
];

const STEPS = [
  { icon: Globe, title: "Collect", desc: "Scrapers continuously pull mentions from public sources." },
  { icon: Brain, title: "Analyze", desc: "AI scores sentiment, extracts entities & keywords." },
  { icon: Zap, title: "Detect", desc: "Rolling analytics flag spikes and rule matches." },
  { icon: Bell, title: "Notify", desc: "Real-time alerts hit your dashboard, inbox & API." },
];

const STATS = [
  { value: "8", label: "Public sources" },
  { value: "<1s", label: "Alert latency" },
  { value: "7", label: "Microservices" },
  { value: "99.9%", label: "Pipeline uptime" },
];

const FAQ = [
  { q: "What sources does EchoscopeAI monitor?", a: "Reddit, NewsAPI, RSS feeds and blogs out of the box — with a pluggable source system to add more." },
  { q: "How is sentiment computed?", a: "A fast lexicon model by default, with optional transformer models (RoBERTa) and GPT summaries when enabled." },
  { q: "Is it real-time?", a: "Yes — events flow through Kafka and reach your dashboard over WebSockets in under a second." },
  { q: "Can I export data?", a: "Generate PDF and CSV reports on demand or on a schedule, stored securely with pre-signed download links." },
];

export default function Landing() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="blob left-[-10%] top-[-10%] h-[420px] w-[420px] bg-brand-400" />
        <div className="blob right-[-5%] top-[10%] h-[360px] w-[360px] bg-accent-400" />
        <div className="container-x relative z-10 grid items-center gap-12 py-20 lg:grid-cols-2 lg:py-28">
          <div>
            <span className="eyebrow"><Sparkles size={14} /> AI-powered social listening</span>
            <h1 className="mt-5 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Know what the internet <span className="gradient-text">says about you</span> — instantly.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600 dark:text-slate-300">
              EchoscopeAI monitors public sources, analyzes sentiment with AI, detects spikes,
              and alerts you in real time — so you protect your reputation before it’s a crisis.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/register" className="btn-gradient text-base">Get started free <ArrowRight size={18} /></Link>
              <Link href="/login" className="btn-soft text-base">Sign in</Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500 dark:text-slate-400">
              <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={16} className="text-emerald-500" /> No credit card</span>
              <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={16} className="text-emerald-500" /> Real-time alerts</span>
              <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={16} className="text-emerald-500" /> Export anytime</span>
            </div>
          </div>
          <div className="relative z-10"><DashboardPreview /></div>
        </div>
      </section>

      {/* STATS */}
      <section className="border-y border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="container-x grid grid-cols-2 gap-6 py-10 md:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-extrabold gradient-text">{s.value}</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="container-x py-20 lg:py-28">
        <div className="mx-auto max-w-2xl text-center">
          <span className="eyebrow"><Radar size={14} /> Everything in one place</span>
          <h2 className="mt-4 text-3xl font-bold sm:text-4xl">A complete listening platform</h2>
          <p className="mt-3 text-slate-600 dark:text-slate-300">From collection to AI analysis to alerting and reporting — built on a production-grade, event-driven architecture.</p>
        </div>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-6 transition hover:shadow-glow">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-600 to-accent-600 text-white">
                <f.icon size={20} />
              </span>
              <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="border-y border-slate-200 bg-slate-50 py-20 dark:border-slate-800 dark:bg-slate-900/40 lg:py-28">
        <div className="container-x">
          <div className="mx-auto max-w-2xl text-center">
            <span className="eyebrow"><Zap size={14} /> How it works</span>
            <h2 className="mt-4 text-3xl font-bold sm:text-4xl">From mention to action in seconds</h2>
          </div>
          <div className="mt-14 grid gap-6 md:grid-cols-4">
            {STEPS.map((s, i) => (
              <div key={s.title} className="relative card p-6 text-center">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-950/40">
                  <s.icon size={22} />
                </span>
                <h3 className="mt-4 font-semibold">{i + 1}. {s.title}</h3>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ANALYTICS SHOWCASE */}
      <section id="analytics" className="container-x grid items-center gap-12 py-20 lg:grid-cols-2 lg:py-28">
        <div>
          <span className="eyebrow"><BarChart3 size={14} /> Analytics</span>
          <h2 className="mt-4 text-3xl font-bold sm:text-4xl">Turn noise into <span className="gradient-text">insight</span></h2>
          <p className="mt-4 text-slate-600 dark:text-slate-300">
            Rolling aggregation, sentiment trends, top keywords, source breakdowns and side-by-side
            competitor scoring — all queryable and cached for instant dashboards.
          </p>
          <ul className="mt-6 space-y-3">
            {["Sentiment trends over any window", "Z-score spike detection & alerting", "Competitor comparison scoring", "Exportable PDF & CSV reports"].map((t) => (
              <li key={t} className="flex items-center gap-3 text-sm">
                <CheckCircle2 size={18} className="text-emerald-500" /> {t}
              </li>
            ))}
          </ul>
          <Link href="/register" className="btn-gradient mt-8 inline-flex">Explore the dashboard <ArrowRight size={18} /></Link>
        </div>
        <DashboardPreview />
      </section>

      {/* FAQ */}
      <section id="faq" className="border-t border-slate-200 bg-slate-50 py-20 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="container-x max-w-3xl">
          <div className="text-center">
            <span className="eyebrow"><Users size={14} /> FAQ</span>
            <h2 className="mt-4 text-3xl font-bold sm:text-4xl">Frequently asked questions</h2>
          </div>
          <div className="mt-10 space-y-4">
            {FAQ.map((f) => (
              <div key={f.q} className="card p-5">
                <h3 className="font-semibold">{f.q}</h3>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container-x py-20">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-brand-600 to-accent-600 px-8 py-16 text-center text-white shadow-glow">
          <h2 className="text-3xl font-bold sm:text-4xl">Start monitoring your brand today</h2>
          <p className="mx-auto mt-3 max-w-xl text-white/90">Set up your first keyword in minutes and watch mentions, sentiment and alerts roll in live.</p>
          <Link href="/register" className="btn mt-8 rounded-full bg-white px-6 py-3 text-base font-semibold text-brand-700 hover:bg-white/90">
            Create your free account <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
