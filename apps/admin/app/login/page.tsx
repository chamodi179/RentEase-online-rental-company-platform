"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function AdminLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/auth/login", { email, password });
      // Hard navigation rather than router.push("/"): this guarantees a
      // brand-new request that definitely carries the cookie we just
      // received, and can't be served from any client-side router cache
      // (see (dashboard)/layout.tsx for why a stale cached response was
      // the actual cause of the redirect-back-to-/login behavior).
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <div>
          <p className="font-semibold text-graphite">RentEase Admin</p>
          <p className="text-sm text-graphite-soft">Staff and Super Admin only</p>
        </div>
        <input type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="input" />
        <div className="relative">
          <input
            type={showPassword ? "text" : "password"}
            required
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input pr-16"
          />
          <button
            type="button"
            onClick={() => setShowPassword((s) => !s)}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-xs font-medium text-graphite-soft hover:text-graphite"
            tabIndex={-1}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <button className="btn-primary w-full" disabled={loading}>{loading ? "Logging in…" : "Log in"}</button>
      </form>
    </div>
  );
}
