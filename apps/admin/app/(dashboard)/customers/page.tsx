"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Customer, DocumentRecord } from "@/lib/types";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [pendingDocs, setPendingDocs] = useState<DocumentRecord[]>([]);
  const [q, setQ] = useState("");

  function loadCustomers() {
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    api.get<Customer[]>(`/customers${query}`).then(setCustomers).catch(() => setCustomers([]));
  }

  function loadPendingDocs() {
    api.get<DocumentRecord[]>("/customers/documents/pending").then(setPendingDocs).catch(() => setPendingDocs([]));
  }

  useEffect(loadCustomers, [q]);
  useEffect(loadPendingDocs, []);

  async function review(docId: number, verification_status: "approved" | "rejected") {
    await api.post(`/customers/documents/${docId}/review`, { verification_status });
    loadPendingDocs();
  }

  // doc.file_url points straight at a private MinIO object — opening it
  // directly 403s (AccessDenied), since the presigned PUT used at upload
  // time only ever authorized that one write, not a later read. Fetch a
  // short-lived presigned GET on click instead.
  async function viewDocument(docId: number) {
    try {
      const { view_url } = await api.get<{ view_url: string }>(`/customers/documents/${docId}/view-url`);
      window.open(view_url, "_blank", "noreferrer");
    } catch {
      alert("Could not load this document.");
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-graphite">Customers</h1>

      <div className="mb-8">
        <h2 className="mb-3 text-sm font-medium text-graphite-soft">Pending document verification</h2>
        {pendingDocs.length === 0 ? (
          <p className="card text-graphite-soft">Nothing pending review.</p>
        ) : (
          <div className="space-y-2">
            {pendingDocs.map((doc) => (
              <div key={doc.id} className="card flex items-center justify-between">
                <div>
                  <p className="font-medium text-graphite">{doc.document_type}</p>
                  <button onClick={() => viewDocument(doc.id)} className="text-sm text-action hover:underline">
                    View document
                  </button>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => review(doc.id, "approved")} className="btn-secondary">Approve</button>
                  <button onClick={() => review(doc.id, "rejected")} className="btn-secondary text-danger">Reject</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

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
