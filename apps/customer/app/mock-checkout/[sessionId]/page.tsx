"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "@/lib/api";
import type { Booking } from "@/lib/types";

// Stand-in for the real Stripe-hosted checkout page. Only reachable when
// STRIPE_SECRET_KEY is the local placeholder — see README "Paying for and
// cancelling a booking (local dev)". Swap in a real key and /payments/checkout
// redirects straight to real Stripe instead; this page is never used.
export default function MockCheckoutPage({ params }: { params: { sessionId: string } }) {
  return (
    <Suspense fallback={<div className="mx-auto max-w-md px-4 py-16 text-ink-soft">Loading…</div>}>
      <MockCheckoutContent sessionId={params.sessionId} />
    </Suspense>
  );
}

function MockCheckoutContent({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const bookingId = searchParams.get("booking_id");
  const [status, setStatus] = useState<"idle" | "paying" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function simulatePayment() {
    if (!bookingId) return;
    setStatus("paying");
    setError(null);
    try {
      const booking = await api.post<Booking>(`/payments/mock-complete/${bookingId}`);
      router.push(`/account/bookings/${booking.id}`);
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Could not complete mock payment");
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <div className="card text-center">
        <p className="mb-1 text-xs uppercase tracking-wide text-ink-soft">Mock checkout — local dev only</p>
        <h1 className="mb-4 font-display text-xl font-semibold text-ink">Confirm test payment</h1>
        <p className="mb-6 text-sm text-ink-soft">
          No real Stripe account is configured, so this stands in for the hosted
          Stripe Checkout page. Session <span className="font-mono">{sessionId}</span>.
        </p>

        {error && <p className="mb-4 text-sm text-danger">{error}</p>}

        <button className="btn-primary w-full" onClick={simulatePayment} disabled={status === "paying" || !bookingId}>
          {status === "paying" ? "Processing…" : "Simulate successful payment"}
        </button>

        {!bookingId && (
          <p className="mt-3 text-sm text-danger">Missing booking reference — go back and start checkout again.</p>
        )}
      </div>
    </div>
  );
}
