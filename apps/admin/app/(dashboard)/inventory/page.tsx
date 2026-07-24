"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdminItem } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  available: "bg-ok/10 text-ok",
  rented: "bg-action/10 text-action",
  maintenance: "bg-warn/10 text-warn",
  retired: "bg-graphite-soft/10 text-graphite-soft",
};

export default function InventoryPage() {
  const [items, setItems] = useState<AdminItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    catalog_id: "", branch_id: "", name: "", description: "",
    base_price_daily: "", deposit_amount: "0",
  });
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<AdminItem[]>("/items").then(setItems).catch(() => setItems([]));
  }

  useEffect(load, []);

  async function createItem(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/items", {
        catalog_id: Number(form.catalog_id),
        branch_id: Number(form.branch_id),
        name: form.name,
        description: form.description || null,
        base_price_daily: form.base_price_daily,
        deposit_amount: form.deposit_amount,
      });
      setShowForm(false);
      setForm({ catalog_id: "", branch_id: "", name: "", description: "", base_price_daily: "", deposit_amount: "0" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create item");
    }
  }

  async function setStatus(id: number, status: string) {
    await api.patch(`/items/${id}`, { status });
    load();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-graphite">Inventory</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "Add item"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={createItem} className="card mb-6 grid grid-cols-2 gap-3">
          <input required placeholder="Catalog ID" value={form.catalog_id} onChange={(e) => setForm({ ...form, catalog_id: e.target.value })} className="input" />
          <input required placeholder="Branch ID" value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })} className="input" />
          <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input col-span-2" />
          <input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input col-span-2" />
          <input required placeholder="Base price / day" value={form.base_price_daily} onChange={(e) => setForm({ ...form, base_price_daily: e.target.value })} className="input" />
          <input placeholder="Deposit amount" value={form.deposit_amount} onChange={(e) => setForm({ ...form, deposit_amount: e.target.value })} className="input" />
          {error && <p className="col-span-2 text-sm text-danger">{error}</p>}
          <button className="btn-primary col-span-2">Create item</button>
        </form>
      )}

      <div className="table-shell">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Name</th>
              <th className="th">Price / day</th>
              <th className="th">Deposit</th>
              <th className="th">Status</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <tr><td className="td text-graphite-soft" colSpan={5}>No items yet.</td></tr>}
            {items.map((item) => (
              <tr key={item.id}>
                <td className="td font-medium">{item.name}</td>
                <td className="td">${item.base_price_daily}</td>
                <td className="td">${item.deposit_amount}</td>
                <td className="td">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLE[item.status]}`}>{item.status}</span>
                </td>
                <td className="td">
                  <select
                    defaultValue={item.status}
                    onChange={(e) => setStatus(item.id, e.target.value)}
                    className="rounded-card border border-line px-2 py-1 text-xs"
                  >
                    <option value="available">available</option>
                    <option value="maintenance">maintenance</option>
                    <option value="retired">retired</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
