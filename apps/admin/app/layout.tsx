import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "RentEase Admin",
  description: "Staff dashboard for RentEase bookings, inventory, and payments.",
};

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/bookings", label: "Bookings" },
  { href: "/inventory", label: "Inventory" },
  { href: "/customers", label: "Customers" },
  { href: "/payments", label: "Payments" },
  { href: "/staff", label: "Staff" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">
        <div className="flex min-h-screen">
          <aside className="w-56 shrink-0 border-r border-line bg-surface">
            <div className="border-b border-line px-5 py-5">
              <p className="font-semibold tracking-tight text-graphite">RentEase</p>
              <p className="text-xs text-graphite-soft">Staff dashboard</p>
            </div>
            <nav className="flex flex-col gap-0.5 p-3">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-card px-3 py-2 text-sm text-graphite-soft hover:bg-action/10 hover:text-graphite"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>

          <div className="flex-1">
            <header className="flex items-center justify-end border-b border-line bg-surface px-6 py-3">
              <Link href="/login" className="text-sm text-graphite-soft hover:text-graphite">
                Log out
              </Link>
            </header>
            <main className="p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
