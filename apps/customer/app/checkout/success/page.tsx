"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Booking } from "@/lib/types";

// useSearchParams() requires a Suspense boundary in the App Router, or the
// build fails during static prerendering — mirrors /checkout/page.tsx.
export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl px-4 py-16 text-ink-soft">Loading…</div>}>
      <CheckoutSuccessContent />
    </Suspense>
  );
}

type SyncState = "checking" | "confirmed" | "pending" | "error";

function CheckoutSuccessContent() {
  const params = useSearchParams();
  const bookingId = params.get("booking_id");
  const sessionId = params.get("session_id");

  const [booking, setBooking] = useState<Booking | null>(null);
  const [state, setState] = useState<SyncState>("checking");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!bookingId || !sessionId) {
      setState("error");
      setError("Missing booking or session reference.");
      return;
    }

    let cancelled = false;
    let attempts = 0;

    // Stripe test-mode payments settle immediately, so the very first sync
    // call almost always confirms. This retry loop is a safety net for the
    // rare case the webhook (the real source of truth) hasn't landed yet —
    // it does NOT replace the webhook, just covers the gap on this screen.
    async function poll() {
      attempts += 1;
      try {
        const updated = await api.get<Booking>(
          `/payments/checkout/${bookingId}/sync?session_id=${encodeURIComponent(sessionId!)}`
        );
        if (cancelled) return;
        setBooking(updated);
        if (updated.status === "pending" && attempts < 5) {
          setState("pending");
          setTimeout(poll, 1500);
        } else {
          setState(updated.status === "pending" ? "pending" : "confirmed");
        }
      } catch (e) {
        if (cancelled) return;
        setState("error");
        setError(e instanceof Error ? e.message : "Could not verify payment");
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [bookingId, sessionId]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center">
      {state === "checking" && <p className="text-ink-soft">Confirming your payment…</p>}

      {state === "pending" && (
        <div className="card">
          <p className="text-ink-soft">Payment received — finalizing your booking…</p>
        </div>
      )}

      {state === "confirmed" && booking && (
        <div className="card">
          <p className="font-display text-lg font-semibold text-ink">Booking confirmed 🎉</p>
          <p className="mt-1 text-ink-soft">
            Reference: <span className="font-medium text-ink">{booking.booking_reference}</span>
          </p>
          <a href={`/account/bookings/${booking.id}`} className="btn-primary mt-5 inline-block">
            View booking
          </a>
        </div>
      )}

      {state === "error" && (
        <div className="card">
          <p className="text-danger">{error}</p>
          <p className="mt-2 text-sm text-ink-soft">
            If money left your account, your booking will still confirm automatically shortly —
            check <a href="/account/bookings" className="underline">My Bookings</a> in a moment.
          </p>
        </div>
      )}
    </div>
  );
}
