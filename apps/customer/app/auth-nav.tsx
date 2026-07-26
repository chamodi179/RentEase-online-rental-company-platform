"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export default function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined); // undefined = still checking
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await api.post("/auth/logout");
    } catch {
      // even if the request fails, drop local state and send them home
    } finally {
      setUser(null);
      setLoggingOut(false);
      router.push("/");
      router.refresh();
    }
  }

  if (user === undefined) {
    // avoid flashing "Log in" before we know the real state
    return <span className="!py-1.5 !px-4 text-sm invisible">Log in</span>;
  }

  if (!user) {
    return (
      <Link href="/login" className="btn-secondary !py-1.5 !px-4 text-sm">
        Log in
      </Link>
    );
  }

  return (
    <button
      onClick={handleLogout}
      disabled={loggingOut}
      className="btn-secondary !py-1.5 !px-4 text-sm"
    >
      {loggingOut ? "Logging out…" : "Log out"}
    </button>
  );
}
