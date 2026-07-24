import Link from "next/link";
import { api } from "@/lib/api";
import type { ItemListing } from "@/lib/types";

async function getItems(): Promise<ItemListing[]> {
  try {
    return await api.get<ItemListing[]>("/items");
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const items = await getItems();

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <section className="mb-10">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
          Real availability. Book online. No more phone tag.
        </h1>
        <p className="mt-2 max-w-xl text-ink-soft">
          Pick your dates and see exactly what&apos;s free — pay online and get a
          confirmed booking reference on the spot.
        </p>
        <form action="/search" className="mt-6 flex max-w-2xl gap-3 rounded-card border border-line bg-white p-3">
          <input name="q" placeholder="Search items…" className="input flex-1 !border-0" />
          <button className="btn-primary shrink-0">Search</button>
        </form>
      </section>

      <section>
        <h2 className="mb-4 font-display text-lg font-semibold text-ink">Available now</h2>
        {items.length === 0 ? (
          <p className="card text-ink-soft">
            Nothing available right now — check back soon, or try the search page for a specific date range.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <Link key={item.id} href={`/items/${item.id}`} className="card block hover:border-ink transition-colors">
                <div className="mb-3 aspect-[4/3] w-full overflow-hidden rounded-card bg-line">
                  {item.photos[0] && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.photos[0].url} alt={item.name} className="h-full w-full object-cover" />
                  )}
                </div>
                <h3 className="font-medium text-ink">{item.name}</h3>
                <p className="text-sm text-ink-soft">{item.branch.city}</p>
                <p className="mt-2 font-medium text-ink">${item.base_price_daily} / day</p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
