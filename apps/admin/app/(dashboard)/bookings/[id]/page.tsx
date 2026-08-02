"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookingDetail } from "@/lib/types";
import { useBookingEvents } from "@/lib/useBookingEvents";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-warn/10 text-warn",
  confirmed: "bg-ok/10 text-ok",
  active: "bg-action/10 text-action",
  completed: "bg-graphite-soft/10 text-graphite-soft",
  cancelled: "bg-danger/10 text-danger",
  refunded: "bg-graphite-soft/10 text-graphite-soft",
};

// booking.status itself never becomes "refunded" — the state machine only
// knows "cancelled" (see ALLOWED_TRANSITIONS in booking_service.py), and
// refund is a separate action that can happen well after cancelling, or
// not at all. is_refunded is computed server-side from the payments table;
// this is purely a display distinction on top of it.
function displayStatus(booking: BookingDetail): string {
  return booking.status === "cancelled" && booking.is_refunded ? "refunded" : booking.status;
}

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

  // If this exact booking changes elsewhere (another admin's tab, a
  // customer self-cancelling, the Stripe webhook confirming payment),
  // reflect it here without a manual reload. Ignore events for other
  // bookings — no need to refetch this page over unrelated activity.
  useBookingEvents((event) => {
    if (String(event.booking_id) === params.id) load();
  });

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

  async function refund() {
    setUpdating(true);
    setError(null);
    try {
      await api.post(`/payments/${params.id}/refund`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not issue refund");
    } finally {
      setUpdating(false);
    }
  }

  if (error && !booking) return <p className="card text-danger">{error}</p>;
  if (!booking) return <p className="card text-graphite-soft">Loading…</p>;

  // refund_booking_payment() is idempotent per booking — once a refund row
  // exists (success, failed, OR pending), calling it again just returns
  // that same row rather than trying again. The API also requires the
  // booking to already be "cancelled" (can't refund an in-progress
  // rental without cancelling it first) — mirrored here so the button
  // doesn't show up somewhere it would just 400.
  const hasRefundablePayment =
    booking.status === "cancelled" &&
    booking.payments.some((p) => p.type === "payment" && p.status === "success") &&
    !booking.payments.some((p) => p.type === "refund");

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-graphite">{booking.booking_reference}</h1>
          <span className={`badge mt-1 inline-block ${STATUS_STYLE[displayStatus(booking)]}`}>{displayStatus(booking)}</span>
        </div>
        <div className="flex gap-2">
          {NEXT_STATUS[booking.status]?.map((s) => (
            <button key={s} disabled={updating} onClick={() => transition(s)} className="btn-secondary">
              Mark {s}
            </button>
          ))}
          {/* Cancelling a confirmed, not-yet-picked-up booking already
              refunds automatically (see admin_initiated in
              cancel_booking()) — this button is for the remaining case:
              a cancelled booking whose auto-refund didn't fire (see the
              payment history below) or a customer's own past
              cancellation where staff want to waive the 48h/24h
              forfeiture. The API requires "cancelled" first — refunding
              an in-progress rental isn't allowed without cancelling it. */}
          {hasRefundablePayment && (
            <button disabled={updating} onClick={refund} className="btn-secondary">
              Refund
            </button>
          )}
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

      <div className="card mt-4">
        <p className="mb-3 text-xs uppercase tracking-wide text-graphite-soft">Payment history</p>
        {booking.payments.length === 0 ? (
          <p className="text-sm text-graphite-soft">No payments recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-graphite-soft">
                <th className="pb-2 font-normal">Type</th>
                <th className="pb-2 font-normal">Amount</th>
                <th className="pb-2 font-normal">Method</th>
                <th className="pb-2 font-normal">Status</th>
                <th className="pb-2 font-normal">Date</th>
              </tr>
            </thead>
            <tbody>
              {booking.payments.map((p) => (
                <tr key={p.id} className="border-t border-line">
                  <td className="py-2 capitalize text-graphite">{p.type}</td>
                  <td className="py-2 text-graphite">${p.amount}</td>
                  <td className="py-2 text-graphite-soft">{p.method}</td>
                  <td className="py-2">
                    <span className={`badge ${p.status === "success" ? "bg-ok/10 text-ok" : p.status === "failed" ? "bg-danger/10 text-danger" : "bg-warn/10 text-warn"}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-2 text-graphite-soft">{new Date(p.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {booking.payments.some((p) => p.type === "refund" && p.status !== "success") && (
          <p className="mt-3 text-sm text-warn">
            A refund here didn&apos;t complete automatically and needs manual follow-up (e.g. a cash/bank-transfer
            refund to hand over, or a failed Stripe call to retry from the Stripe dashboard directly).
          </p>
        )}
      </div>

      <div className="card mt-4">
        <p className="mb-3 text-xs uppercase tracking-wide text-graphite-soft">Audit trail</p>
        {booking.audit_log.length === 0 ? (
          <p className="text-sm text-graphite-soft">No recorded actions yet.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {booking.audit_log.map((entry) => (
              <li key={entry.id} className="flex justify-between gap-4 border-t border-line pt-2 first:border-t-0 first:pt-0">
                <span className="text-graphite">{entry.action}</span>
                <span className="shrink-0 text-graphite-soft">
                  {entry.actor_name ?? "System"} · {new Date(entry.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
