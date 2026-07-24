"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookingDetail } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-warn/10 text-warn",
  confirmed: "bg-ok/10 text-ok",
  active: "bg-action/10 text-action",
  completed: "bg-graphite-soft/10 text-graphite-soft",
  cancelled: "bg-danger/10 text-danger",
};

// Mirrors ALLOWED_TRANSITIONS in booking_service.py — the API is the real
// enforcement point, this just avoids showing buttons that would 400.
const NEXT_STATUS: Record<string, string[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["active", "cancelled"],
  active: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

export default function AdminBookingDetailPage({ params }: { params: { id: string } }) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  function load() {
    api.get<BookingDetail>(`/bookings/${params.id}`).then(setBooking).catch(() => setError("Booking not found"));
  }

  useEffect(load, [params.id]);

  async function transition(newStatus: string) {
    setUpdating(true);
    setError(null);
    try {
      await api.post(`/bookings/${params.id}/status`, { new_status: newStatus });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update status");
    } finally {
      setUpdating(false);
    }
  }

  if (error && !booking) return <p className="card text-danger">{error}</p>;
  if (!booking) return <p className="card text-graphite-soft">Loading…</p>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-graphite">{booking.booking_reference}</h1>
          <span className={`badge mt-1 inline-block ${STATUS_STYLE[booking.status]}`}>{booking.status}</span>
        </div>
        <div className="flex gap-2">
          {NEXT_STATUS[booking.status]?.map((s) => (
            <button key={s} disabled={updating} onClick={() => transition(s)} className="btn-secondary">
              Mark {s}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-graphite-soft">Item</p>
          <p className="mt-1 font-medium text-graphite">{booking.item.name}</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-graphite-soft">Customer ID</p>
          <p className="mt-1 font-medium text-graphite">#{booking.customer_id}</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-graphite-soft">Pickup</p>
          <p className="mt-1 text-graphite">{booking.branch_pickup.name}, {booking.branch_pickup.city}</p>
          <p className="text-sm text-graphite-soft">{new Date(booking.start_datetime).toLocaleString()}</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-graphite-soft">Drop-off</p>
          <p className="mt-1 text-graphite">{booking.branch_dropoff.name}, {booking.branch_dropoff.city}</p>
          <p className="text-sm text-graphite-soft">{new Date(booking.end_datetime).toLocaleString()}</p>
        </div>
      </div>

      <div className="card mt-4">
        <p className="mb-3 text-xs uppercase tracking-wide text-graphite-soft">Payment breakdown</p>
        <dl className="space-y-1.5 text-sm">
          <div className="flex justify-between text-graphite-soft"><dt>Base</dt><dd>${booking.base_amount}</dd></div>
          <div className="flex justify-between text-graphite-soft"><dt>Tax</dt><dd>${booking.tax_amount}</dd></div>
          <div className="flex justify-between text-graphite-soft"><dt>Deposit</dt><dd>${booking.deposit_amount}</dd></div>
          <div className="flex justify-between font-medium text-graphite"><dt>Total</dt><dd>${booking.total_amount}</dd></div>
        </dl>
      </div>
    </div>
  );
}
