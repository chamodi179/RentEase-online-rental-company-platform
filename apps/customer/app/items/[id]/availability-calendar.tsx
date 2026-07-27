"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { BookedRange } from "@/lib/types";

function toDateOnly(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function fmtISO(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export default function AvailabilityCalendar({
  itemId,
  selectedStart,
  selectedEnd,
  onSelect,
}: {
  itemId: number;
  selectedStart: string; // yyyy-mm-dd, may be ""
  selectedEnd: string;
  onSelect: (start: string, end: string) => void;
}) {
  const [bookedRanges, setBookedRanges] = useState<BookedRange[]>([]);
  const [loading, setLoading] = useState(true);
  const [monthOffset, setMonthOffset] = useState(0); // months ahead of the current month
  // Two-click range selection: first click sets a pending start, second
  // click (on a later date) commits the range via onSelect.
  const [pendingStart, setPendingStart] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .get<BookedRange[]>(`/items/${itemId}/availability?months=3`)
      .then(setBookedRanges)
      .catch(() => setBookedRanges([]))
      .finally(() => setLoading(false));
  }, [itemId]);

  const blockedDays = useMemo(() => {
    // Expand each booked range into a Set of yyyy-mm-dd strings for O(1)
    // per-cell lookups while rendering the grid.
    const set = new Set<string>();
    for (const range of bookedRanges) {
      const start = toDateOnly(new Date(range.start_datetime));
      const end = toDateOnly(new Date(range.end_datetime));
      const cursor = new Date(start);
      while (cursor < end) {
        set.add(fmtISO(cursor));
        cursor.setDate(cursor.getDate() + 1);
      }
    }
    return set;
  }, [bookedRanges]);

  const today = toDateOnly(new Date());

  function monthGrid(monthsFromNow: number) {
    const base = new Date(today.getFullYear(), today.getMonth() + monthsFromNow, 1);
    const year = base.getFullYear();
    const month = base.getMonth();
    const firstWeekday = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells: (Date | null)[] = [];
    for (let i = 0; i < firstWeekday; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));

    return { year, month, cells };
  }

  function isInSelectedRange(iso: string) {
    if (!selectedStart || !selectedEnd) return false;
    return iso >= selectedStart && iso < selectedEnd;
  }

  function handleDayClick(date: Date) {
    const iso = fmtISO(date);
    if (blockedDays.has(iso) || date < today) return;

    if (!pendingStart) {
      setPendingStart(iso);
      onSelect(iso, "");
      return;
    }

    if (iso <= pendingStart) {
      // Clicking an earlier (or same) date restarts the selection instead
      // of producing an inverted/zero-length range.
      setPendingStart(iso);
      onSelect(iso, "");
      return;
    }

    // Reject a range that would cross a blocked day in the middle.
    const cursor = new Date(pendingStart);
    const endDate = new Date(iso);
    let crossesBlocked = false;
    while (cursor < endDate) {
      if (blockedDays.has(fmtISO(cursor))) {
        crossesBlocked = true;
        break;
      }
      cursor.setDate(cursor.getDate() + 1);
    }
    if (crossesBlocked) {
      setPendingStart(iso);
      onSelect(iso, "");
      return;
    }

    onSelect(pendingStart, iso);
    setPendingStart(null);
  }

  const { year, month, cells } = monthGrid(monthOffset);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setMonthOffset((m) => Math.max(0, m - 1))}
          disabled={monthOffset === 0}
          className="rounded-card px-2 py-1 text-sm text-ink-soft hover:bg-line disabled:opacity-30"
          aria-label="Previous month"
        >
          ←
        </button>
        <p className="text-sm font-medium text-ink">{MONTH_NAMES[month]} {year}</p>
        <button
          type="button"
          onClick={() => setMonthOffset((m) => Math.min(2, m + 1))}
          disabled={monthOffset === 2}
          className="rounded-card px-2 py-1 text-sm text-ink-soft hover:bg-line disabled:opacity-30"
          aria-label="Next month"
        >
          →
        </button>
      </div>

      {loading ? (
        <p className="py-6 text-center text-sm text-ink-soft">Loading availability…</p>
      ) : (
        <>
          <div className="grid grid-cols-7 gap-1 text-center text-xs text-ink-soft">
            {WEEKDAYS.map((w, i) => (
              <div key={i} className="py-1">{w}</div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((date, i) => {
              if (!date) return <div key={i} />;
              const iso = fmtISO(date);
              const isPast = date < today;
              const isBlocked = blockedDays.has(iso);
              const isSelected = iso === selectedStart || iso === selectedEnd || isInSelectedRange(iso);
              const isPendingStart = iso === pendingStart;

              let classes = "aspect-square rounded-card text-xs flex items-center justify-center ";
              if (isPast) classes += "text-ink-soft/30 cursor-not-allowed";
              else if (isBlocked) classes += "bg-danger/10 text-danger/60 cursor-not-allowed line-through";
              else if (isSelected || isPendingStart) classes += "bg-amber text-ink font-medium cursor-pointer";
              else classes += "text-ink hover:bg-line cursor-pointer";

              return (
                <button
                  type="button"
                  key={i}
                  disabled={isPast || isBlocked}
                  onClick={() => handleDayClick(date)}
                  className={classes}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>
        </>
      )}

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-soft">
        <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-amber" /> Selected</span>
        <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-danger/40" /> Booked</span>
      </div>
      <p className="mt-1 text-xs text-ink-soft">
        {pendingStart ? "Pick an end date." : "Click a start date, then an end date."}
      </p>
    </div>
  );
}
