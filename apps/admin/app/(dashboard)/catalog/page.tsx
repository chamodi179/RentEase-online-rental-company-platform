"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AdminCatalog, Category } from "@/lib/types";

export default function CatalogPage() {
  const [catalog, setCatalog] = useState<AdminCatalog[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [newCategoryId, setNewCategoryId] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<AdminCatalog[]>("/items/catalog").then(setCatalog).catch(() => setCatalog([]));
    api.get<Category[]>("/items/categories").then(setCategories).catch(() => setCategories([]));
  }

  useEffect(load, []);

  async function createCatalogEntry(e: React.FormEvent) {
    e.preventDefault();
    if (!newCategoryId) return;
    setError(null);
    setCreating(true);
    try {
      await api.post("/items/catalog", { category_id: Number(newCategoryId) });
      setNewCategoryId("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create catalog entry");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-graphite">Catalog &amp; Photos</h1>
          <p className="text-sm text-graphite-soft">
            Each catalog entry is an item model — photos live here and are shared by every physical unit of
            that model (see Inventory for individual rentable units).
          </p>
        </div>
      </div>

      <form onSubmit={createCatalogEntry} className="card mb-6 flex items-end gap-3">
        <label className="text-sm text-graphite-soft">
          New catalog entry — category
          <select
            required
            value={newCategoryId}
            onChange={(e) => setNewCategoryId(e.target.value)}
            className="mt-1 block rounded-card border border-line px-3 py-2 text-sm"
          >
            <option value="">Select a category…</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <button className="btn-primary" disabled={creating || !newCategoryId}>
          {creating ? "Creating…" : "Create catalog entry"}
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      <div className="space-y-4">
        {catalog.length === 0 && <p className="card text-graphite-soft">No catalog entries yet.</p>}
        {catalog.map((entry) => (
          <CatalogCard key={entry.id} entry={entry} onChange={load} />
        ))}
      </div>
    </div>
  );
}

function CatalogCard({ entry, onChange }: { entry: AdminCatalog; onChange: () => void }) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function uploadPhoto(file: File) {
    setError(null);
    setUploading(true);
    try {
      // Same presign -> direct PUT -> register flow as the customer app's
      // document upload (routers/admin/items.py presign_catalog_photo /
      // register_catalog_photo) — the API never proxies the file bytes.
      const { upload_url, file_url } = await api.post<{ upload_url: string; file_url: string }>(
        `/items/catalog/${entry.id}/photos/presign`,
        { filename: file.name, content_type: file.type || "application/octet-stream" }
      );
      const putRes = await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });
      if (!putRes.ok) throw new Error(`Upload to storage failed (${putRes.status})`);

      await api.post(`/items/catalog/${entry.id}/photos`, {
        file_url,
        sort_order: entry.photos.length,
      });
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload photo");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function deletePhoto(photoId: number) {
    await api.delete(`/items/catalog/photos/${photoId}`);
    onChange();
  }

  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="font-medium text-graphite">Catalog #{entry.id} — {entry.category?.name ?? "Uncategorized"}</p>
          <p className="text-xs text-graphite-soft">{entry.photos.length} photo(s)</p>
        </div>
        <label className="btn-secondary cursor-pointer text-sm">
          {uploading ? "Uploading…" : "Add photo"}
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            className="hidden"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) uploadPhoto(file);
            }}
          />
        </label>
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {entry.photos.length > 0 && (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
          {[...entry.photos]
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((photo) => (
              <div key={photo.id} className="group relative aspect-square overflow-hidden rounded-card bg-line">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.url} alt="" className="h-full w-full object-cover" />
                <button
                  onClick={() => deletePhoto(photo.id)}
                  className="absolute right-1 top-1 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white opacity-0 transition group-hover:opacity-100"
                >
                  Remove
                </button>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
