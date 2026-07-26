import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import AuthNav from "./auth-nav";

export const metadata: Metadata = {
  title: "RentEase",
  description: "Browse, book, and pay for rentals online — no more phone-and-WhatsApp double bookings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col font-body">
        <header className="border-b border-line bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <Link href="/" className="font-display text-xl font-semibold tracking-tight text-ink">
              RentEase
            </Link>
            <nav className="flex items-center gap-6 text-sm text-ink-soft">
              <Link href="/" className="hover:text-ink">Browse</Link>
              <Link href="/search" className="hover:text-ink">Search</Link>
              <Link href="/account/bookings" className="hover:text-ink">My Bookings</Link>
              <AuthNav />
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="mt-16 border-t border-line bg-white">
          <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-ink-soft flex flex-wrap gap-6 justify-between">
            <p>&copy; {new Date().getFullYear()} RentEase</p>
            <div className="flex gap-5">
              <Link href="/about" className="hover:text-ink">About Us</Link>
              <Link href="/terms" className="hover:text-ink">Terms &amp; Conditions</Link>
              <Link href="/privacy" className="hover:text-ink">Privacy Policy</Link>
              <Link href="/contact" className="hover:text-ink">Contact Us</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
