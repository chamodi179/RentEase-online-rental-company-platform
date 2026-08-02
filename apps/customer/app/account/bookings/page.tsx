"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Booking } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-pending/10 text-pending",
  confirmed: "bg-available/10 text-available",
  active: "bg-available/10 text-available",
  completed: "bg-ink-soft/10 text-ink-soft",
  cancelled: "bg-danger/10 text-danger",
  refunded: "bg-ink-soft/10 text-ink-soft",
};

// b.status only ever says "cancelled" — is_refunded (computed server-side)
// is what actually tells you whether the money came back. Grouping
// (groupOf, below) intentionally still buckets these under "cancelled" —
// only the badge text/color changes.
function displayStatus(b: Booking): string {
  return b.status === "cancelled" && b.is_refunded ? "refunded" : b.status;
}

// Spec §4.3: "My Bookings: upcoming, active, past, cancelled". Bookings
// don't carry a "group" field directly — it's derived from status (and, for
// pending/confirmed, whether the pickup date has already passed).
type Group = "upcoming" | "active" | "past" | "cancelled";

function groupOf(b: Booking): Group {
  if (b.status === "cancelled") return "cancelled";
  if (b.status === "active") return "active";
  if (b.status === "completed") return "past";
  // pending or confirmed
  return new Date(b.start_datetime) < new Date() ? "past" : "upcoming";
}

const TABS: { key: "all" | Group; label: string }[] = [
  { key: "all", label: "All" },
  { key: "upcoming", label: "Upcoming" },
  { key: "active", label: "Active" },
  { key: "past", label: "Past" },
  { key: "cancelled", label: "Cancelled" },
];

export default function MyBookingsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("all");

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings).catch(() => setError(true));
  }, []);

  const counts = useMemo(() => {
    const c: Record<Group, number> = { upcoming: 0, active: 0, past: 0, cancelled: 0 };
    (bookings ?? []).forEach((b) => c[groupOf(b)]++);
    return c;
  }, [bookings]);

  const filtered = useMemo(() => {
    if (!bookings) return [];
    if (tab === "all") return bookings;
    return bookings.filter((b) => groupOf(b) === tab);
  }, [bookings, tab]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl font-semibold text-ink">My Bookings</h1>

      {error && (
        <p className="card text-ink-soft">
          Log in to see your bookings. <Link href="/login" className="text-ink underline">Log in</Link>
        </p>
      )}

      {bookings && (
        <div className="mb-5 flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                tab === t.key ? "bg-ink text-paper" : "bg-line/60 text-ink-soft hover:bg-line"
              }`}
            >
              {t.label}
              {t.key !== "all" && counts[t.key] > 0 && (
                <span className="ml-1.5 opacity-70">{counts[t.key]}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {bookings && bookings.length === 0 && <p className="card text-ink-soft">No bookings yet — browse items to get started.</p>}

      {bookings && bookings.length > 0 && filtered.length === 0 && (
        <p className="card text-ink-soft">No bookings in this category.</p>
      )}

      {filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map((b) => (
            <Link key={b.id} href={`/account/bookings/${b.id}`} className="card flex items-center justify-between hover:border-ink">
              <div>
                <p className="font-medium text-ink">{b.booking_reference}</p>
                <p className="text-sm text-ink-soft">{new Date(b.start_datetime).toLocaleDateString()} → {new Date(b.end_datetime).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLE[displayStatus(b)]}`}>{displayStatus(b)}</span>
                <span className="font-medium text-ink">${b.total_amount}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
