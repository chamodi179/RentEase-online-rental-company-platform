"use client";

import { useSearchParams } from "next/navigation";
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
  const params = useSearchParams();
  const itemId = params.get("item_id");
  const start = params.get("start");
  const end = params.get("end");

  const [step, setStep] = useState<Step>("review");
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [quote, setQuote] = useState<PriceQuote | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docUploaded, setDocUploaded] = useState(false);
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docUploading, setDocUploading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  // Booking is created once and reused on retry — see createBookingAndPay().
  const [bookingId, setBookingId] = useState<number | null>(null);
  const [paying, setPaying] = useState(false);

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
    if (!docFile) {
      setDocError("Choose a file first.");
      return;
    }
    setDocError(null);
    setDocUploading(true);
    try {
      // 1. Ask the API for a presigned MinIO URL for this filename.
      const { upload_url, file_url } = await api.post<{ upload_url: string; file_url: string }>(
        "/documents/presign",
        { filename: docFile.name, content_type: docFile.type || "application/octet-stream" }
      );

      // 2. Upload the actual file bytes directly to MinIO (not through the API —
      // the API never proxies file bytes, see architecture doc §7). Plain PUT
      // with no cookies/credentials, so don't use the api.* wrapper here.
      const putRes = await fetch(upload_url, {
        method: "PUT",
        body: docFile,
        headers: { "Content-Type": docFile.type || "application/octet-stream" },
      });
      if (!putRes.ok) {
        throw new Error(`Upload to storage failed (${putRes.status})`);
      }

      // 3. Register the now-real file_url against the booking.
      await api.post("/documents", { document_type: "id_card", file_url });

      setDocUploaded(true);
      setStep("payment");
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Could not upload document");
    } finally {
      setDocUploading(false);
    }
  }

  async function createBookingAndPay() {
    setError(null);
    setPaying(true);
    try {
      // Only create the booking on the *first* attempt. A pending booking
      // legitimately blocks its own window (see availability.py), so if a
      // previous click got this far and then failed later (e.g. reaching
      // Stripe), retrying must reuse that same booking instead of creating
      // a second one — otherwise the retry collides with itself and comes
      // back as "Item is already booked for this window".
      let id = bookingId;
      if (id === null) {
        const created = await api.post<Booking>("/bookings", {
          item_id: Number(itemId),
          branch_pickup_id: item?.branch.id,
          branch_dropoff_id: item?.branch.id,
          start_datetime: `${start}T10:00:00`,
          end_datetime: `${end}T10:00:00`,
        });
        id = created.id;
        setBookingId(id);
      }
      const session = await api.post<{ checkout_url: string }>(`/payments/checkout/${id}`);
      // Real Stripe-hosted checkout. Stripe redirects back to /checkout/success
      // (or straight back here on cancel) — the "done" step below is never
      // reached from this page; it's rendered on the success page instead.
      window.location.href = session.checkout_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not complete booking");
      setPaying(false);
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
          <input
            type="file"
            accept="image/*,application/pdf"
            className="input mb-4"
            onChange={(e) => {
              setDocFile(e.target.files?.[0] ?? null);
              setDocError(null);
            }}
          />
          {docError && <p className="mb-3 text-sm text-danger">{docError}</p>}
          <button className="btn-primary w-full" onClick={submitDocument} disabled={docUploading}>
            {docUploading ? "Uploading…" : "Upload & continue"}
          </button>
          {docUploaded && <p className="mt-2 text-sm text-available">Document uploaded.</p>}
        </div>
      )}

      {step === "payment" && (
        <div className="card">
          <p className="mb-4 text-ink-soft">Pay securely via Stripe to confirm your booking.</p>
          {error && (
            <p className="mb-3 text-sm text-danger">
              {error}
              {bookingId && " — your reservation is still held, just try paying again."}
            </p>
          )}
          <button className="btn-primary w-full" onClick={createBookingAndPay} disabled={paying}>
            {paying ? "Redirecting to Stripe…" : "Pay & confirm booking"}
          </button>
        </div>
      )}
    </div>
  );
}
