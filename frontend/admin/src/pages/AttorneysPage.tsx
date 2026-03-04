import { useEffect, useState, useCallback, type FormEvent } from "react";
import { apiFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface UserRecord {
  id: string;
  email: string;
  role: "ADMIN" | "ATTORNEY";
  is_active: boolean;
  created_at: string;
}

export default function AttorneysPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    try {
      const data = await apiFetch<UserRecord[]>("/api/admin/users");
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    setFormLoading(true);
    try {
      const created = await apiFetch<UserRecord>("/api/admin/attorneys", {
        method: "POST",
        body: JSON.stringify({ email: newEmail, password: newPassword }),
      });
      setUsers((prev) => [created, ...prev]);
      setNewEmail("");
      setNewPassword("");
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create attorney");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDeactivate(id: string) {
    setActionLoading(id);
    try {
      const updated = await apiFetch<UserRecord>(`/api/admin/users/${id}/deactivate`, {
        method: "PATCH",
      });
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deactivation failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReactivate(id: string) {
    setActionLoading(id);
    try {
      const updated = await apiFetch<UserRecord>(`/api/admin/users/${id}/reactivate`, {
        method: "PATCH",
      });
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reactivation failed");
    } finally {
      setActionLoading(null);
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-stone-500">
        Admin access required.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-stone-500">
        Loading users...
      </div>
    );
  }

  const attorneys = users.filter((u) => u.role === "ATTORNEY");
  const activeCount = attorneys.filter((u) => u.is_active).length;
  const inactiveCount = attorneys.filter((u) => !u.is_active).length;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">Attorneys</h2>
          <p className="text-sm text-stone-500">
            {attorneys.length} {attorneys.length === 1 ? "attorney" : "attorneys"}
            {" "}({activeCount} active, {inactiveCount} deactivated)
          </p>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          {showForm ? "Cancel" : "Add Attorney"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-2 font-medium underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 rounded-lg border border-stone-200 bg-white p-6 shadow-sm"
        >
          <h3 className="mb-4 text-sm font-semibold text-stone-800">
            New Attorney Account
          </h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-700">
                Email
              </label>
              <input
                type="email"
                required
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="block w-full rounded-md border border-stone-300 px-3 py-2 text-sm placeholder:text-stone-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="attorney@alma.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-700">
                Password
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="block w-full rounded-md border border-stone-300 px-3 py-2 text-sm placeholder:text-stone-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="Min. 6 characters"
              />
            </div>
          </div>

          {formError && (
            <p className="mt-3 text-sm text-red-600">{formError}</p>
          )}

          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={formLoading}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {formLoading ? "Creating..." : "Create Attorney"}
            </button>
          </div>
        </form>
      )}

      {attorneys.length === 0 ? (
        <div className="rounded-lg border border-stone-200 bg-white py-12 text-center text-sm text-stone-500">
          No attorneys yet. Click "Add Attorney" to create one.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-stone-200">
            <thead className="bg-stone-50">
              <tr>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Email
                </th>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Created
                </th>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Status
                </th>
                <th className="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wide text-stone-500">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {attorneys.map((atty, i) => (
                <tr
                  key={atty.id}
                  className={`${i % 2 === 1 ? "bg-stone-50/50" : ""} hover:bg-stone-50`}
                >
                  <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-stone-900">
                    {atty.email}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-sm text-stone-500">
                    {formatDate(atty.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4">
                    <StatusBadge active={atty.is_active} />
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-right">
                    {atty.is_active ? (
                      <button
                        onClick={() => handleDeactivate(atty.id)}
                        disabled={actionLoading === atty.id}
                        className="rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {actionLoading === atty.id ? "Deactivating..." : "Deactivate"}
                      </button>
                    ) : (
                      <button
                        onClick={() => handleReactivate(atty.id)}
                        disabled={actionLoading === atty.id}
                        className="rounded-md border border-emerald-300 px-3 py-1.5 text-xs font-medium text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                      >
                        {actionLoading === atty.id ? "Reactivating..." : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  const styles = active
    ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
    : "bg-red-50 text-red-700 ring-red-200";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles}`}
    >
      {active ? "Active" : "Deactivated"}
    </span>
  );
}
