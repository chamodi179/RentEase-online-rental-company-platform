import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import type { ItemDetail } from "@/lib/types";
import BookingWidget from "./booking-widget";

async function getItem(id: string): Promise<ItemDetail | null> {
  try {
    return await api.get<ItemDetail>(`/items/${id}`);
  } catch {
    return null;
  }
}

export default async function ItemDetailPage({ params }: { params: { id: string } }) {
  const item = await getItem(params.id);
  if (!item) notFound();

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="mb-4 aspect-video w-full overflow-hidden rounded-card bg-line">
            {item.photos[0] && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={item.photos[0].url} alt={item.name} className="h-full w-full object-cover" />
            )}
          </div>
          {item.photos.length > 1 && (
            <div className="grid grid-cols-4 gap-3">
              {item.photos.slice(1).map((p) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={p.id} src={p.url} alt="" className="aspect-square rounded-card object-cover" />
              ))}
            </div>
          )}

          <h1 className="mt-6 font-display text-2xl font-semibold text-ink">{item.name}</h1>
          <p className="text-ink-soft">{item.category?.name} · {item.branch.name}, {item.branch.city}</p>
          <p className="mt-4 text-ink-soft">{item.description}</p>
        </div>

        <div className="lg:col-span-2">
          <BookingWidget item={item} />
        </div>
      </div>
    </div>
  );
}
