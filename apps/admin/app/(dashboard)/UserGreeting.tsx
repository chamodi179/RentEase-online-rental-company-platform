"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

// Same pattern as LogoutButton: this has to be a client component because
// api.ts relies on the browser's cookie jar (credentials: "include"), which
// a server component fetch doesn't have access to. See the comment at the
// top of the (old) dashboard page.tsx for the full explanation.
export default function UserGreeting() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  if (!user) return null;

  return (
    <span className="text-sm text-graphite-soft">
      Signed in as <span className="font-medium text-graphite">{user.full_name}</span>
    </span>
  );
}
