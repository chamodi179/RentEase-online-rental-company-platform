"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const MIN_PASSWORD_LENGTH = 8;

function passwordIssue(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) return `At least ${MIN_PASSWORD_LENGTH} characters.`;
  if (!/[a-zA-Z]/.test(password)) return "Include at least one letter.";
  if (!/[0-9]/.test(password)) return "Include at least one number.";
  return null;
}

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update(field: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Client-side check mirrors the server-side policy in
    // schemas/common.py::RegisterIn (see validate_password_strength) —
    // this just gives faster feedback; the server is still the source of
    // truth and re-validates on submit.
    const issue = passwordIssue(form.password);
    if (issue) {
      setError(issue);
      return;
    }
    if (form.password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/auth/register", { ...form, phone: form.phone.trim() || null });
      await api.post("/auth/login", { email: form.email, password: form.password });
      router.push("/account/bookings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16">
      <h1 className="mb-6 font-display text-2xl font-semibold text-ink">Create an account</h1>
      <form onSubmit={submit} className="space-y-4">
        <input required placeholder="Full name" value={form.full_name} onChange={update("full_name")} className="input" />
        <input type="email" required placeholder="Email" value={form.email} onChange={update("email")} className="input" />
        <input placeholder="Phone (optional)" value={form.phone} onChange={update("phone")} className="input" />
        <div>
          <input type="password" required placeholder="Password" value={form.password} onChange={update("password")} className="input" />
          <p className="mt-1 text-xs text-ink-soft">At least {MIN_PASSWORD_LENGTH} characters, with a letter and a number.</p>
        </div>
        <input
          type="password"
          required
          placeholder="Confirm password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="input"
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <button className="btn-primary w-full" disabled={loading}>{loading ? "Creating…" : "Create account"}</button>
      </form>
      <p className="mt-4 text-sm text-ink-soft">
        Already have an account? <Link href="/login" className="text-ink underline">Log in</Link>
      </p>
    </div>
  );
}
