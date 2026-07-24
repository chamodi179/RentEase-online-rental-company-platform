import Link from "next/link";
import { api } from "@/lib/api";
import type { ItemListing } from "@/lib/types";

async function searchItems(params: { q?: string; start?: string; end?: string }): Promise<ItemListing[]> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  try {
    return await api.get<ItemListing[]>(`/items?${query.toString()}`);
  } catch {
    return [];
  }
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: { q?: string; start?: string; end?: string };
}) {
  const items = await searchItems(searchParams);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl font-semibold text-ink">Search &amp; availability</h1>

      <form className="card mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <input name="q" defaultValue={searchParams.q} placeholder="Keyword" className="input sm:col-span-2" />
        <input type="date" name="start" defaultValue={searchParams.start} className="input" />
        <input type="date" name="end" defaultValue={searchParams.end} className="input" />
        <button className="btn-primary sm:col-span-4">Check availability</button>
      </form>

      {items.length === 0 ? (
        <p className="card text-ink-soft">No items match that search. Try widening your dates.</p>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <Link key={item.id} href={`/items/${item.id}`} className="card block hover:border-ink transition-colors">
              <h3 className="font-medium text-ink">{item.name}</h3>
              <p className="text-sm text-ink-soft">{item.branch.name} · {item.branch.city}</p>
              <p className="mt-2 font-medium text-ink">${item.base_price_daily} / day</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
