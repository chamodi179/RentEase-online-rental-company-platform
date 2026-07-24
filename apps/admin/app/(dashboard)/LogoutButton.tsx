"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function LogoutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    try {
      await api.post("/auth/logout");
    } catch {
      // Even if the network call fails, still send the user to /login —
      // there's nothing useful to do with the error here.
    }
    // Hard navigation (not router.push): guarantees a clean request with
    // no stale client-router cache, and forces middleware to re-evaluate
    // from scratch now that the cookie has been cleared.
    window.location.href = "/login";
  }

  return (
    <button
      onClick={handleLogout}
      disabled={loading}
      className="text-sm text-graphite-soft hover:text-graphite disabled:opacity-50"
    >
      {loading ? "Logging out…" : "Log out"}
    </button>
  );
}
