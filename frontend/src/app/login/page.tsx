"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/api/v1/auth/login", { email, password });
      setTokens(data.access_token, data.refresh_token);
      try {
        const me = await api.get("/api/v1/auth/me");
        setUser(me.data);
      } catch { /* token still set */ }
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch {
      toast.error("Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-2xl font-bold tracking-tight">Sign in to your account</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Monitor your brand in real time.</p>

      <form onSubmit={submit} className="mt-8 space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium">Email</label>
          <input className="input" type="email" placeholder="you@company.com" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Password</label>
          <input className="input" type="password" placeholder="••••••••" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn-gradient w-full justify-center !py-2.5 text-base" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
        Don’t have an account?{" "}
        <Link href="/register" className="font-medium text-brand-600 hover:underline">Create one free</Link>
      </p>
    </AuthShell>
  );
}
