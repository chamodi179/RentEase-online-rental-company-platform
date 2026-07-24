import { api } from "@/lib/api";
import type { AdminBooking, DashboardSummary } from "@/lib/types";

async function getSummary(): Promise<DashboardSummary | null> {
  try {
    return await api.get<DashboardSummary>("/dashboard/summary");
  } catch {
    return null;
  }
}

async function getTodaysBookings(): Promise<AdminBooking[]> {
  try {
    const today = new Date().toISOString().slice(0, 10);
    return await api.get<AdminBooking[]>(`/bookings?start_from=${today}T00:00:00&start_to=${today}T23:59:59`);
  } catch {
    return [];
  }
}

export default async function DashboardPage() {
  const [summary, todays] = await Promise.all([getSummary(), getTodaysBookings()]);

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-graphite">Dashboard</h1>

      {!summary ? (
        <p className="card text-graphite-soft">Log in to view the dashboard.</p>
      ) : (
        <>
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="card">
              <p className="text-xs uppercase tracking-wide text-graphite-soft">Today&apos;s pickups</p>
              <p className="mt-2 text-3xl font-semibold text-graphite">{summary.todays_pickups}</p>
            </div>
            <div className="card">
              <p className="text-xs uppercase tracking-wide text-graphite-soft">Today&apos;s returns</p>
              <p className="mt-2 text-3xl font-semibold text-graphite">{summary.todays_returns}</p>
            </div>
            <div className="card">
              <p className="text-xs uppercase tracking-wide text-graphite-soft">Active rentals</p>
              <p className="mt-2 text-3xl font-semibold text-graphite">{summary.active_rentals}</p>
            </div>
          </div>

          <h2 className="mb-3 text-sm font-medium text-graphite-soft">Today&apos;s bookings</h2>
          <div className="table-shell">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">Reference</th>
                  <th className="th">Status</th>
                  <th className="th">Start</th>
                  <th className="th">End</th>
                  <th className="th">Total</th>
                </tr>
              </thead>
              <tbody>
                {todays.length === 0 && (
                  <tr><td className="td text-graphite-soft" colSpan={5}>Nothing scheduled today.</td></tr>
                )}
                {todays.map((b) => (
                  <tr key={b.id}>
                    <td className="td font-medium">{b.booking_reference}</td>
                    <td className="td">{b.status}</td>
                    <td className="td">{new Date(b.start_datetime).toLocaleTimeString()}</td>
                    <td className="td">{new Date(b.end_datetime).toLocaleTimeString()}</td>
                    <td className="td">${b.total_amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
