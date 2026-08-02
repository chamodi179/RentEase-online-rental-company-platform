"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Payment, User } from "@/lib/types";
import { useBookingEvents } from "@/lib/useBookingEvents";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-warn/10 text-warn",
  success: "bg-ok/10 text-ok",
  failed: "bg-danger/10 text-danger",
};

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ booking_id: "", type: "payment", amount: "", method: "cash", gateway_reference: "" });
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<Payment[]>("/payments").then(setPayments).catch(() => setPayments([]));
  }

  useEffect(load, []);
  useEffect(() => {
    api.get<User>("/auth/me").then(setUser).catch(() => setUser(null));
  }, []);

  // Same channel as the bookings pages — a payment/refund recorded here,
  // by another admin tab, or by the automatic pre-pickup refund on cancel,
  // should show up without a manual reload.
  useBookingEvents(() => load());

  // Manual payment/refund recording bypasses Stripe entirely and is
  // trusted at face value, so — same as the backend (routers/admin/
  // payments.py: record_manual_payment requires super_admin) — only
  // super_admin sees the form to do it. Regular staff can still view the
  // ledger below.
  const canRecordManualPayment = user?.role === "super_admin";

  async function recordPayment(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/payments", {
        booking_id: Number(form.booking_id),
        type: form.type,
        amount: form.amount,
        method: form.method,
        gateway_reference: form.gateway_reference || null,
      });
      setShowForm(false);
      setForm({ booking_id: "", type: "payment", amount: "", method: "cash", gateway_reference: "" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record payment");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-graphite">Payments</h1>
        {canRecordManualPayment && (
          <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "Record manual payment"}
          </button>
        )}
      </div>

      {!canRecordManualPayment && user && (
        <p className="mb-6 text-sm text-graphite-soft">
          Manual payments and refunds can only be recorded by a super_admin. You&apos;re signed in as {user.role}.
        </p>
      )}

      {showForm && canRecordManualPayment && (
        <form onSubmit={recordPayment} className="card mb-6 grid grid-cols-2 gap-3">
          <input required placeholder="Booking ID" value={form.booking_id} onChange={(e) => setForm({ ...form, booking_id: e.target.value })} className="input" />
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="input">
            <option value="payment">payment</option>
            <option value="refund">refund</option>
          </select>
          <input required placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="input" />
          <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} className="input">
            <option value="cash">cash</option>
            <option value="bank_transfer">bank_transfer</option>
            <option value="card">card</option>
          </select>
          <input placeholder="Gateway reference (optional)" value={form.gateway_reference} onChange={(e) => setForm({ ...form, gateway_reference: e.target.value })} className="input col-span-2" />
          {error && <p className="col-span-2 text-sm text-danger">{error}</p>}
          <button className="btn-primary col-span-2">Record payment</button>
        </form>
      )}

      <div className="table-shell">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Booking</th>
              <th className="th">Type</th>
              <th className="th">Amount</th>
              <th className="th">Method</th>
              <th className="th">Status</th>
            </tr>
          </thead>
          <tbody>
            {payments.length === 0 && <tr><td className="td text-graphite-soft" colSpan={5}>No transactions yet.</td></tr>}
            {payments.map((p) => (
              <tr key={p.id}>
                <td className="td font-medium">#{p.booking_id}</td>
                <td className="td">{p.type}</td>
                <td className="td">${p.amount}</td>
                <td className="td">{p.method}</td>
                <td className="td"><span className={`badge ${STATUS_STYLE[p.status]}`}>{p.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
