import { useEffect, useRef } from "react";

export type BookingEvent = {
  event: "created" | "status_changed" | "refunded" | `payment_${string}`;
  booking_id: number;
  booking_reference: string;
  status: string;
};

// Same public/server split as lib/api.ts's API_URL, just ws:// instead of
// http://. This hook only ever runs in the browser (called from "use
// client" pages), so there's no server-side branch to worry about here.
const WS_URL = (process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8002/api/v1").replace(/^http/, "ws");

/**
 * Subscribes to the admin-only booking events feed (see
 * app/routers/admin/realtime.py) and calls onEvent for every message.
 * Reconnects with backoff on drop — a login-session expiry or a brief
 * network blip shouldn't require a page refresh to resume live updates.
 * This is purely a "go re-fetch" signal, never a data source on its own:
 * every page using this still loads its real data over the normal REST
 * API, so a missed or delayed event just means a slightly stale screen
 * until the next one arrives or the page is reloaded manually — never
 * incorrect data.
 */
export function useBookingEvents(onEvent: (event: BookingEvent) => void) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let stopped = false;

    function connect() {
      socket = new WebSocket(`${WS_URL}/ws/bookings`);

      socket.onmessage = (msg) => {
        try {
          onEventRef.current(JSON.parse(msg.data));
        } catch {
          // Malformed payload — ignore rather than crash the page over a
          // live-refresh nicety.
        }
      };

      socket.onclose = () => {
        if (stopped) return;
        // Capped exponential backoff: 1s, 2s, 4s, ... up to 30s. Covers
        // both "server restarted" and "not logged in yet" without hammering
        // the connection.
        const delay = Math.min(30_000, 1000 * 2 ** attempt);
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);
}
