import type { Metadata } from "next";
import "./globals.css";

// Deliberately minimal: no sidebar/nav chrome here. That chrome only
// belongs to authenticated pages and lives in app/(dashboard)/layout.tsx.
// Keeping it out of the root layout means:
//   1. /login never renders with the dashboard shell around it.
//   2. The root layout contains no <Link> to protected routes, so nothing
//      here triggers Next.js's automatic prefetch of "/" before the user
//      has actually logged in (see (dashboard)/layout.tsx for the full
//      explanation of why that prefetch was causing the redirect loop).
export const metadata: Metadata = {
  title: "RentEase Admin",
  description: "Staff dashboard for RentEase bookings, inventory, and payments.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
