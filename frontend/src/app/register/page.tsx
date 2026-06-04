"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", org_name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/api/v1/auth/register", form);
      toast.success("Account created — please sign in");
      router.push("/login");
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-2xl font-bold tracking-tight">Create your account</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Start monitoring in minutes — no credit card.</p>

      <form onSubmit={submit} className="mt-8 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Full name</label>
            <input className="input" placeholder="Ada Lovelace" required value={form.full_name} onChange={set("full_name")} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">Organization</label>
            <input className="input" placeholder="Acme Inc" required value={form.org_name} onChange={set("org_name")} />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Email</label>
          <input className="input" type="email" placeholder="you@company.com" required value={form.email} onChange={set("email")} />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">Password</label>
          <input className="input" type="password" placeholder="At least 8 characters" required minLength={8} value={form.password} onChange={set("password")} />
        </div>
        <button className="btn-gradient w-full justify-center !py-2.5 text-base" disabled={loading}>
          {loading ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand-600 hover:underline">Sign in</Link>
      </p>
    </AuthShell>
  );
}
