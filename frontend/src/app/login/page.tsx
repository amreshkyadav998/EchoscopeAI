"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { Radar } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { ThemeToggle } from "@/components/theme-toggle";

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
      } catch { /* gateway may not be running for /me; token still set */ }
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch {
      toast.error("Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="absolute right-4 top-4"><ThemeToggle /></div>
      <div className="card w-full max-w-md p-8">
        <div className="mb-6 flex items-center gap-2">
          <Radar className="text-brand-600" />
          <span className="text-xl font-bold">EchoscopeAI</span>
        </div>
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Monitor your brand in real time.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <input className="input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn-primary w-full" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
          No account? <Link href="/register" className="text-brand-600 hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  );
}
