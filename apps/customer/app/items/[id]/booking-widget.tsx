"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { ItemDetail, PriceQuote } from "@/lib/types";
import AvailabilityCalendar from "./availability-calendar";

export default function BookingWidget({ item }: { item: ItemDetail }) {
  const router = useRouter();
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [quote, setQuote] = useState<PriceQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleCalendarSelect(newStart: string, newEnd: string) {
    setStart(newStart);
    setEnd(newEnd);
    setQuote(null);
    setError(null);
  }

  async function getQuote() {
    setError(null);
    setQuote(null);
    if (!start || !end) return;
    try {
      const q = await api.get<PriceQuote>(
        `/items/${item.id}/quote?start=${start}T10:00:00&end=${end}T10:00:00`
      );
      setQuote(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not price this window");
    }
  }

  async function proceedToCheckout() {
    if (!start || !end) return;
    setLoading(true);
    // Booking details are passed via query string to the checkout page,
    // which creates the booking after login + document upload (spec §4.2).
    const params = new URLSearchParams({ item_id: String(item.id), start, end });
    router.push(`/checkout?${params.toString()}`);
    setLoading(false);
  }

  return (
    <div className="card sticky top-6">
      <p className="text-2xl font-semibold text-ink">
        ${item.base_price_daily}
        <span className="text-base font-normal text-ink-soft"> / day</span>
      </p>
      <p className="mt-1 text-sm text-ink-soft">Deposit: ${item.deposit_amount}</p>

      <div className="mt-5 border-t border-line pt-4">
        <AvailabilityCalendar
          itemId={item.id}
          selectedStart={start}
          selectedEnd={end}
          onSelect={handleCalendarSelect}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="text-sm text-ink-soft">
          Start
          <input type="date" value={start} onChange={(e) => { setStart(e.target.value); setQuote(null); }} className="input mt-1" />
        </label>
        <label className="text-sm text-ink-soft">
          End
          <input type="date" value={end} onChange={(e) => { setEnd(e.target.value); setQuote(null); }} className="input mt-1" />
        </label>
      </div>

      <button onClick={getQuote} className="btn-secondary mt-4 w-full">Check price &amp; availability</button>

      {error && <p className="mt-3 text-sm text-danger">{error}</p>}

      {quote && (
        <dl className="mt-4 space-y-1.5 border-t border-line pt-4 text-sm">
          <div className="flex justify-between text-ink-soft">
            <dt>Base rate × {quote.days} day(s)</dt><dd>${quote.base_amount}</dd>
          </div>
          <div className="flex justify-between text-ink-soft">
            <dt>Deposit</dt><dd>${quote.deposit_amount}</dd>
          </div>
          <div className="flex justify-between font-medium text-ink">
            <dt>Total due</dt><dd>${quote.total_amount}</dd>
          </div>
        </dl>
      )}

      <button
        onClick={proceedToCheckout}
        disabled={!quote || loading}
        className="btn-primary mt-4 w-full"
      >
        {loading ? "Please wait…" : "Book this item"}
      </button>
    </div>
  );
}
