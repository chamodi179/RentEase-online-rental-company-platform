"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BookingDetail, CancelBookingResult } from "@/lib/types";

// 48h refund window (spec §4.3). Cancellation is *always* allowed for
// pending/confirmed bookings — this only determines whether it's a full
// refund or not; it never blocks the cancel button itself.
const FREE_CANCEL_HOURS = 48;

function hoursUntilPickup(startISO: string) {
  return (new Date(startISO).getTime() - Date.now()) / 36e5;
}

const REFUND_MESSAGES: Record<string, string> = {
  success: "Cancelled — your payment has been refunded in full.",
  pending: "Cancelled — a full refund is due and will be processed manually; you'll be notified once it's issued.",
  failed: "Cancelled — the automatic refund failed. Our team will follow up to process it manually.",
};

export default function BookingDetailPage({ params }: { params: { id: string } }) {
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelResult, setCancelResult] = useState<CancelBookingResult | null>(null);

  useEffect(() => {
    api.get<BookingDetail>(`/bookings/${params.id}`).then(setBooking).catch(() => setLoadError("Booking not found"));
  }, [params.id]);

  async function cancel() {
    setCancelling(true);
    setCancelError(null);
    try {
      const updated = await api.post<CancelBookingResult>(`/bookings/${params.id}/cancel`);
      setBooking((b) => (b ? { ...b, status: updated.status } : b));
      setCancelResult(updated);
    } catch (e) {
      setCancelError(e instanceof Error ? e.message : "Could not cancel");
    } finally {
      setCancelling(false);
    }
  }

  if (loadError) return <div className="mx-auto max-w-2xl px-4 py-16 text-danger">{loadError}</div>;
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

      {cancelError && <p className="mt-4 text-sm text-danger">{cancelError}</p>}

      {cancelResult && (
        <p className="mt-6 text-sm text-ink">
          {cancelResult.refund_status ? REFUND_MESSAGES[cancelResult.refund_status] : "Booking cancelled."}
        </p>
      )}

      {!cancelResult && ["pending", "confirmed"].includes(booking.status) && (
        <div className="mt-6">
          <p className="mb-2 text-sm text-ink-soft">
            {hoursUntilPickup(booking.start_datetime) >= FREE_CANCEL_HOURS
              ? `You're outside the ${FREE_CANCEL_HOURS}h window — cancelling now gets a full refund.`
              : `You're within ${FREE_CANCEL_HOURS}h of pickup — cancelling now won't be refunded.`}
          </p>
          <button onClick={cancel} disabled={cancelling} className="btn-secondary">
            {cancelling ? "Cancelling…" : "Cancel booking"}
          </button>
        </div>
      )}
    </div>
  );
}
