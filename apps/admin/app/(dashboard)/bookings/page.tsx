"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdminBooking } from "@/lib/types";
import { useBookingEvents } from "@/lib/useBookingEvents";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-warn/10 text-warn",
  confirmed: "bg-ok/10 text-ok",
  active: "bg-action/10 text-action",
  completed: "bg-graphite-soft/10 text-graphite-soft",
  cancelled: "bg-danger/10 text-danger",
  refunded: "bg-graphite-soft/10 text-graphite-soft",
};

// Same distinction as the detail page: booking.status only ever says
// "cancelled" — is_refunded (computed server-side in list_bookings) is
// what actually tells you whether the money came back.
function displayStatus(b: AdminBooking): string {
  return b.status === "cancelled" && b.is_refunded ? "refunded" : b.status;
}

export default function BookingsPage() {
  const [bookings, setBookings] = useState<AdminBooking[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    customer_id: "", item_id: "", branch_pickup_id: "", branch_dropoff_id: "",
    start_datetime: "", end_datetime: "",
  });
  const [error, setError] = useState<string | null>(null);

  function load() {
    const q = statusFilter ? `?status_filter=${statusFilter}` : "";
    api.get<AdminBooking[]>(`/bookings${q}`).then(setBookings).catch(() => setBookings([]));
  }

  useEffect(load, [statusFilter]);

  // Any booking being created or changing status (by this admin, another
  // admin, a customer, or the Stripe webhook) should show up here without
  // a manual reload. Simplest correct approach: any event just re-runs the
  // same load() the page already does on mount/filter-change — no separate
  // patch-in-place logic to keep in sync with the filter/sort/pagination.
  useBookingEvents(() => load());

  async function createManualBooking(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/bookings", {
        customer_id: Number(form.customer_id),
        item_id: Number(form.item_id),
        branch_pickup_id: Number(form.branch_pickup_id),
        branch_dropoff_id: Number(form.branch_dropoff_id),
        start_datetime: form.start_datetime,
        end_datetime: form.end_datetime,
      });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create booking");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-graphite">Bookings</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New manual booking"}
        </button>
      </div>

      <div className="mb-4 flex gap-2">
        {["", "pending", "confirmed", "active", "completed", "cancelled"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => setStatusFilter(s)}
            className={`rounded-card border px-3 py-1.5 text-xs font-medium ${
              statusFilter === s ? "border-action bg-action/10 text-action" : "border-line text-graphite-soft"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {showForm && (
        <form onSubmit={createManualBooking} className="card mb-6 grid grid-cols-3 gap-3">
          <input required placeholder="Customer ID" value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} className="input" />
          <input required placeholder="Item ID" value={form.item_id} onChange={(e) => setForm({ ...form, item_id: e.target.value })} className="input" />
          <input required placeholder="Pickup branch ID" value={form.branch_pickup_id} onChange={(e) => setForm({ ...form, branch_pickup_id: e.target.value })} className="input" />
          <input required placeholder="Dropoff branch ID" value={form.branch_dropoff_id} onChange={(e) => setForm({ ...form, branch_dropoff_id: e.target.value })} className="input" />
          <input required type="datetime-local" value={form.start_datetime} onChange={(e) => setForm({ ...form, start_datetime: e.target.value })} className="input" />
          <input required type="datetime-local" value={form.end_datetime} onChange={(e) => setForm({ ...form, end_datetime: e.target.value })} className="input" />
          {error && <p className="col-span-3 text-sm text-danger">{error}</p>}
          <button className="btn-primary col-span-3">Create booking</button>
        </form>
      )}

      <div className="table-shell">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Reference</th>
              <th className="th">Status</th>
              <th className="th">Start</th>
              <th className="th">End</th>
              <th className="th">Total</th>
            </tr>
          </thead>
          <tbody>
            {bookings.length === 0 && <tr><td className="td text-graphite-soft" colSpan={5}>No bookings match this filter.</td></tr>}
            {bookings.map((b) => (
              <tr key={b.id}>
                <td className="td font-medium">
                  <Link href={`/bookings/${b.id}`} className="text-action hover:underline">{b.booking_reference}</Link>
                </td>
                <td className="td"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[displayStatus(b)]}`}>{displayStatus(b)}</span></td>
                <td className="td">{new Date(b.start_datetime).toLocaleString()}</td>
                <td className="td">{new Date(b.end_datetime).toLocaleString()}</td>
                <td className="td">${b.total_amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
