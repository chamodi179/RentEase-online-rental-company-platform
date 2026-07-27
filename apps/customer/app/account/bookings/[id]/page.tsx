"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookingDetail } from "@/lib/types";

// Free cancellation before 48h (spec §4.3 — one simple fixed policy for MVP).
function canCancel(startISO: string) {
  const hoursUntil = (new Date(startISO).getTime() - Date.now()) / 36e5;
  return hoursUntil >= 48;
}

export default function BookingDetailPage({ params }: { params: { id: string } }) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<BookingDetail>(`/bookings/${params.id}`).then(setBooking).catch(() => setError("Booking not found"));
  }, [params.id]);

  async function cancel() {
    setCancelling(true);
    try {
      const updated = await api.post<BookingDetail>(`/bookings/${params.id}/cancel`);
      setBooking((b) => (b ? { ...b, status: updated.status } : b));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not cancel");
    } finally {
      setCancelling(false);
    }
  }

  if (error) return <div className="mx-auto max-w-2xl px-4 py-16 text-danger">{error}</div>;
  if (!booking) return <div className="mx-auto max-w-2xl px-4 py-16 text-ink-soft">Loading…</div>;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-1 font-display text-2xl font-semibold text-ink">{booking.booking_reference}</h1>
      <p className="mb-6 text-ink-soft">Status: <span className="font-medium text-ink">{booking.status}</span></p>

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
      </div>

      {["pending", "confirmed"].includes(booking.status) && (
        <div className="mt-6">
          <button onClick={cancel} disabled={cancelling} className="btn-secondary">
            {cancelling ? "Cancelling…" : "Cancel booking"}
          </button>
          {/* Cancellation is always available (spec §4.3) — only the refund
              outcome depends on timing, and that's the API's call to make,
              not a client-side gate. This is informational only. */}
          <p className="mt-2 text-sm text-ink-soft">
            {booking.status !== "confirmed"
              ? "This booking hasn't been paid yet, so cancelling is free."
              : canCancel(booking.start_datetime)
              ? "You're more than 48h from pickup, so cancelling now gets a full refund."
              : "This booking starts in under 48 hours — cancelling now will not refund your payment."}
          </p>
        </div>
      )}
    </div>
  );
}
