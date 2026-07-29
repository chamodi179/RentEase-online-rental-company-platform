"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const MIN_PASSWORD_LENGTH = 8;

function passwordIssue(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) return `Password needs at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (!/[a-zA-Z]/.test(password)) return "Password needs at least one letter.";
  if (!/[0-9]/.test(password)) return "Password needs at least one number.";
  return null;
}

export default function StaffPage() {
  const [staff, setStaff] = useState<User[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", password: "", role: "staff" });
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function load() {
    // Returns 403 for anyone logged in as "staff" rather than "super_admin" —
    // this page is only useful to super admins, matching spec §5.6.
    api.get<User[]>("/staff").then(setStaff).catch(() => setStaff([]));
  }

  useEffect(load, []);

  async function createStaff(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    // Mirrors the server-side policy in schemas/admin.py::StaffCreateIn —
    // the server re-validates regardless, this just avoids a round trip.
    const issue = passwordIssue(form.password);
    if (issue) {
      setError(issue);
      return;
    }
    try {
      await api.post("/staff", form);
      setShowForm(false);
      setForm({ full_name: "", email: "", phone: "", password: "", role: "staff" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create staff account");
    }
  }

  async function deactivate(id: number) {
    setActionError(null);
    try {
      await api.post(`/staff/${id}/deactivate`);
      load();
    } catch (err) {
      // e.g. self-deactivation or "last active super_admin" guard on the backend
      setActionError(err instanceof Error ? err.message : "Could not deactivate this account");
    }
  }

  async function reactivate(id: number) {
    setActionError(null);
    try {
      await api.post(`/staff/${id}/reactivate`);
      load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not reactivate this account");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-graphite">Staff &amp; Roles</h1>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "Add staff account"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={createStaff} className="card mb-6 grid grid-cols-2 gap-3">
          <input required placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="input" />
          <input required type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input" />
          <input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input" />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input">
            <option value="staff">staff</option>
            <option value="super_admin">super_admin</option>
          </select>
          <input required type="password" placeholder="Temporary password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="input col-span-2" />
          <p className="col-span-2 -mt-2 text-xs text-graphite-soft">At least {MIN_PASSWORD_LENGTH} characters, with a letter and a number.</p>
          {error && <p className="col-span-2 text-sm text-danger">{error}</p>}
          <button className="btn-primary col-span-2">Create account</button>
        </form>
      )}

      <div className="table-shell">
        {actionError && <p className="border-b border-line px-4 py-2 text-sm text-danger">{actionError}</p>}
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Name</th>
              <th className="th">Email</th>
              <th className="th">Role</th>
              <th className="th">Status</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {staff.length === 0 && <tr><td className="td text-graphite-soft" colSpan={5}>No staff accounts yet, or you need super_admin access to view this page.</td></tr>}
            {staff.map((s) => (
              <tr key={s.id}>
                <td className="td font-medium">{s.full_name}</td>
                <td className="td">{s.email}</td>
                <td className="td">{s.role}</td>
                <td className="td">{s.is_active ? "Active" : "Deactivated"}</td>
                <td className="td">
                  {s.is_active ? (
                    <button onClick={() => deactivate(s.id)} className="btn-secondary text-danger">Deactivate</button>
                  ) : (
                    <button onClick={() => reactivate(s.id)} className="btn-secondary">Reactivate</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
