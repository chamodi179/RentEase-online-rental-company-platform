"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookingDetail } from "@/lib/types";

// Mirrors the backend's customer_can_cancel policy (booking_service.py):
// unpaid bookings can always be self-cancelled; paid ones if EITHER window
// is still open — ≥48h before pickup, or within 24h of payment (using
// updated_at as an approximation of "when it was confirmed" — see the
// caveat on BookingOut.updated_at in schemas/common.py). This is purely
// informational — the API enforces it for real off the audit trail, so a
// stale client-side approximation just means a slightly wrong button
// state, not a bypassable rule.
function canSelfCancel(booking: BookingDetail) {
  if (booking.status === "pending") return true;
  if (booking.status !== "confirmed") return false;
  const hoursUntilPickup = (new Date(booking.start_datetime).getTime() - Date.now()) / 36e5;
  const hoursSincePayment = (Date.now() - new Date(booking.updated_at).getTime()) / 36e5;
  return hoursUntilPickup >= 48 || hoursSincePayment <= 24;
}

// booking.status only ever says "cancelled" — is_refunded (computed
// server-side from the payments table) is what actually distinguishes a
// refunded cancellation from one that isn't (yet, or forfeited).
function displayStatus(booking: BookingDetail) {
  return booking.status === "cancelled" && booking.is_refunded ? "refunded" : booking.status;
}

export default function BookingDetailPage({ params }: { params: { id: string } }) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<BookingDetail>(`/bookings/${params.id}`).then(setBooking).catch(() => setError("Booking not found"));
  }

  useEffect(load, [params.id]);

  async function cancel() {
    setCancelling(true);
    try {
      await api.post(`/bookings/${params.id}/cancel`);
      // Re-fetch the full detail (not just the status) — a self-cancel
      // always refunds when it's allowed at all (see customer_can_cancel),
      // so this is what actually shows that refund landed, instead of
      // just flipping the status badge to "cancelled" with no evidence
      // the money came back.
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not cancel");
    } finally {
      setCancelling(false);
    }
  }

  if (error) return <div className="mx-auto max-w-2xl px-4 py-16 text-danger">{error}</div>;
  if (!booking) return <div className="mx-auto max-w-2xl px-4 py-16 text-ink-soft">Loading…</div>;

  const eligible = canSelfCancel(booking);

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-1 font-display text-2xl font-semibold text-ink">{booking.booking_reference}</h1>
      <p className="mb-6 text-ink-soft">Status: <span className="font-medium text-ink">{displayStatus(booking)}</span></p>

      <div className="card space-y-4">
        <div>
          <p className="text-sm text-ink-soft">Item</p>
          <p className="font-medium text-ink">{booking.item.name}</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-ink-soft">Pickup</p>
            <p className="text-ink">{booking.branch_pickup.name}</p>
            <p className="text-sm text-ink-soft">{new Date(booking.start_datetime).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-sm text-ink-soft">Drop-off</p>
            <p className="text-ink">{booking.branch_dropoff.name}</p>
            <p className="text-sm text-ink-soft">{new Date(booking.end_datetime).toLocaleString()}</p>
          </div>
        </div>
        <dl className="space-y-1 border-t border-line pt-4 text-sm">
          <div className="flex justify-between text-ink-soft"><dt>Base</dt><dd>${booking.base_amount}</dd></div>
          <div className="flex justify-between text-ink-soft"><dt>Tax</dt><dd>${booking.tax_amount}</dd></div>
          <div className="flex justify-between text-ink-soft"><dt>Deposit</dt><dd>${booking.deposit_amount}</dd></div>
          <div className="flex justify-between font-medium text-ink"><dt>Total</dt><dd>${booking.total_amount}</dd></div>
        </dl>

        {booking.payments.length > 0 && (
          <div className="space-y-1.5 border-t border-line pt-4 text-sm">
            <p className="text-ink-soft">Payment history</p>
            {booking.payments.map((p) => (
              <div key={p.id} className="flex justify-between">
                <span className="capitalize text-ink">
                  {p.type} <span className="text-ink-soft">({p.method})</span>
                </span>
                <span className="text-ink-soft">
                  ${p.amount} —{" "}
                  <span className={p.status === "success" ? "text-ok" : p.status === "failed" ? "text-danger" : "text-warn"}>
                    {p.status}
                  </span>
                </span>
              </div>
            ))}
            {booking.payments.some((p) => p.type === "refund" && p.status !== "success") && (
              <p className="pt-1 text-ink-soft">
                Your refund is still being processed — if it&apos;s been a few days, feel free to{" "}
                <a href="/contact" className="underline">contact us</a>.
              </p>
            )}
          </div>
        )}
      </div>

      {["pending", "confirmed"].includes(booking.status) && (
        <div className="mt-6">
          {eligible ? (
            <>
              <button onClick={cancel} disabled={cancelling} className="btn-secondary">
                {cancelling ? "Cancelling…" : "Cancel booking"}
              </button>
              <p className="mt-2 text-sm text-ink-soft">
                {booking.status === "pending"
                  ? "This booking hasn't been paid yet, so cancelling is free."
                  : "Cancelling now gets a full refund — you're either more than 48h from pickup, or within 24h of paying."}
              </p>
            </>
          ) : (
            <p className="text-sm text-ink-soft">
              This booking is outside the free-cancellation window — more than 24h since payment,
              and less than 48h before pickup — so it can&apos;t be cancelled here.{" "}
              <a href="/contact" className="underline">Contact us</a> and our team can cancel it (and refund
              you) if needed.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
