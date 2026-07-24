"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Booking } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-pending/10 text-pending",
  confirmed: "bg-available/10 text-available",
  active: "bg-available/10 text-available",
  completed: "bg-ink-soft/10 text-ink-soft",
  cancelled: "bg-danger/10 text-danger",
};

export default function MyBookingsPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get<Booking[]>("/bookings").then(setBookings).catch(() => setError(true));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl font-semibold text-ink">My Bookings</h1>

      {error && (
        <p className="card text-ink-soft">
          Log in to see your bookings. <Link href="/login" className="text-ink underline">Log in</Link>
        </p>
      )}

      {bookings && bookings.length === 0 && <p className="card text-ink-soft">No bookings yet — browse items to get started.</p>}

      {bookings && bookings.length > 0 && (
        <div className="space-y-3">
          {bookings.map((b) => (
            <Link key={b.id} href={`/account/bookings/${b.id}`} className="card flex items-center justify-between hover:border-ink">
              <div>
                <p className="font-medium text-ink">{b.booking_reference}</p>
                <p className="text-sm text-ink-soft">{new Date(b.start_datetime).toLocaleDateString()} → {new Date(b.end_datetime).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_STYLE[b.status]}`}>{b.status}</span>
                <span className="font-medium text-ink">${b.total_amount}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
