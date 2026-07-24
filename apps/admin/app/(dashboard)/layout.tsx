import Link from "next/link";
import LogoutButton from "./LogoutButton";

// This layout — and its sidebar <Link>s — only applies to routes inside
// the (dashboard) route group, i.e. everything except /login. That
// separation matters for two reasons:
//
//  1. Cosmetic: /login no longer renders with the dashboard shell around
//     it (that's what was happening before — see the root layout).
//
//  2. Functional: Next.js prefetches every <Link> it renders, including
//     the "Dashboard" link (href="/") below. When these links used to
//     live in the *root* layout, they were present on /login too — so
//     Next.js prefetched "/" the moment /login loaded, before the user
//     had authenticated. middleware.ts ran on that prefetch, found no
//     access_token cookie yet, and cached a redirect-to-/login as the
//     result for "/". After a real login, router.push("/") could then
//     serve that stale pre-auth redirect instead of re-checking — which
//     is what was bouncing you straight back to the login page. Scoping
//     these links to the authenticated route group means they're never
//     rendered (and therefore never prefetched) until a session cookie
//     already exists.
const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/bookings", label: "Bookings" },
  { href: "/inventory", label: "Inventory" },
  { href: "/customers", label: "Customers" },
  { href: "/payments", label: "Payments" },
  { href: "/staff", label: "Staff" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
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
          <LogoutButton />
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
