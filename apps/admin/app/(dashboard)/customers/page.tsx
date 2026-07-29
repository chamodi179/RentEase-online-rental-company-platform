"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Customer } from "@/lib/types";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [q, setQ] = useState("");

  function loadCustomers() {
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    api.get<Customer[]>(`/customers${query}`).then(setCustomers).catch(() => setCustomers([]));
  }

  useEffect(loadCustomers, [q]);

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-graphite">Customers</h1>

      <div className="mb-4">
        <input
          placeholder="Search by name or email…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="input max-w-sm"
        />
      </div>

      <div className="table-shell">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Name</th>
              <th className="th">Email</th>
              <th className="th">Verified</th>
              <th className="th">Bookings</th>
            </tr>
          </thead>
          <tbody>
            {customers.length === 0 && <tr><td className="td text-graphite-soft" colSpan={4}>No customers found.</td></tr>}
            {customers.map((c) => (
              <tr key={c.id}>
                <td className="td font-medium">{c.full_name}</td>
                <td className="td">{c.email}</td>
                <td className="td">{c.is_verified ? "Yes" : "No"}</td>
                <td className="td">{c.booking_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
