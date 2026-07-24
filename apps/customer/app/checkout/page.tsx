"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Booking, ItemDetail, PriceQuote, User } from "@/lib/types";

type Step = "review" | "document" | "payment" | "done";

// useSearchParams() requires a Suspense boundary in the App Router, or the
// build fails during static prerendering — this wrapper is that boundary.
export default function CheckoutPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl px-4 py-16 text-ink-soft">Loading…</div>}>
      <CheckoutContent />
    </Suspense>
  );
}

function CheckoutContent() {
  const router = useRouter();
  const params = useSearchParams();
  const itemId = params.get("item_id");
  const start = params.get("start");
  const end = params.get("end");

  const [step, setStep] = useState<Step>("review");
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [quote, setQuote] = useState<PriceQuote | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docUploaded, setDocUploaded] = useState(false);

  useEffect(() => {
    if (!itemId || !start || !end) return;
    api.get<ItemDetail>(`/items/${itemId}`).then(setItem).catch(() => {});
    api
      .get<PriceQuote>(`/items/${itemId}/quote?start=${start}T10:00:00&end=${end}T10:00:00`)
      .then(setQuote)
      .catch(() => {});
    api.get<User>("/auth/me").then(setUser).catch(() => setUser(null));
  }, [itemId, start, end]);

  if (!itemId || !start || !end) {
    return <div className="mx-auto max-w-2xl px-4 py-16 text-ink-soft">Missing booking details — start over from an item page.</div>;
  }

  async function submitDocument() {
    // In production this uploads to the presigned MinIO URL first, then
    // registers the resulting file_url. Stubbed here to a placeholder URL.
    await api.post("/documents", { document_type: "id_card", file_url: "https://minio.rentease.internal/stub.jpg" });
    setDocUploaded(true);
    setStep("payment");
  }

  async function createBookingAndPay() {
    setError(null);
    try {
      const created = await api.post<Booking>("/bookings", {
        item_id: Number(itemId),
        branch_pickup_id: item?.branch.id,
        branch_dropoff_id: item?.branch.id,
        start_datetime: `${start}T10:00:00`,
        end_datetime: `${end}T10:00:00`,
      });
      setBooking(created);
      const session = await api.post<{ checkout_url: string }>(`/payments/checkout/${created.id}`);
      // Production: window.location.href = session.checkout_url (redirect to Stripe).
      // MVP demo: mark done directly since Stripe webhook confirms server-side.
      void session;
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not complete booking");
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl font-semibold text-ink">Checkout</h1>

      <ol className="mb-8 flex gap-4 text-sm text-ink-soft">
        {["Review", "Verify", "Pay", "Done"].map((label, i) => (
          <li key={label} className={["review", "document", "payment", "done"][i] === step ? "font-medium text-ink" : ""}>
            {i + 1}. {label}
          </li>
        ))}
      </ol>

      {item && quote && (
        <div className="card mb-6">
          <p className="font-medium text-ink">{item.name}</p>
          <p className="text-sm text-ink-soft">{start} → {end} ({quote.days} day(s))</p>
          <dl className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between text-ink-soft"><dt>Base</dt><dd>${quote.base_amount}</dd></div>
            <div className="flex justify-between text-ink-soft"><dt>Tax</dt><dd>${quote.tax_amount}</dd></div>
            <div className="flex justify-between text-ink-soft"><dt>Deposit</dt><dd>${quote.deposit_amount}</dd></div>
            <div className="flex justify-between font-medium text-ink"><dt>Total</dt><dd>${quote.total_amount}</dd></div>
          </dl>
        </div>
      )}

      {step === "review" && (
        <div className="card">
          {!user ? (
            <div>
              <p className="mb-3 text-ink-soft">Log in or create an account to continue.</p>
              <div className="flex gap-3">
                <a href="/login" className="btn-secondary">Log in</a>
                <a href="/register" className="btn-primary">Create account</a>
              </div>
            </div>
          ) : (
            <button className="btn-primary w-full" onClick={() => setStep("document")}>Continue as {user.full_name}</button>
          )}
        </div>
      )}

      {step === "document" && (
        <div className="card">
          <p className="mb-3 text-ink-soft">Upload one verification document (e.g. ID) to continue.</p>
          <input type="file" className="input mb-4" />
          <button className="btn-primary w-full" onClick={submitDocument}>Upload &amp; continue</button>
          {docUploaded && <p className="mt-2 text-sm text-available">Document uploaded.</p>}
        </div>
      )}

      {step === "payment" && (
        <div className="card">
          <p className="mb-4 text-ink-soft">Pay securely via Stripe to confirm your booking.</p>
          {error && <p className="mb-3 text-sm text-danger">{error}</p>}
          <button className="btn-primary w-full" onClick={createBookingAndPay}>Pay &amp; confirm booking</button>
        </div>
      )}

      {step === "done" && booking && (
        <div className="card text-center">
          <p className="font-display text-lg font-semibold text-ink">Booking confirmed 🎉</p>
          <p className="mt-1 text-ink-soft">Reference: <span className="font-medium text-ink">{booking.booking_reference}</span></p>
          <button className="btn-primary mt-5" onClick={() => router.push(`/account/bookings/${booking.id}`)}>
            View booking
          </button>
        </div>
      )}
    </div>
  );
}
