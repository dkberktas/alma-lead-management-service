import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../lib/api";

interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  resume_path: string;
  state: "PENDING" | "REACHED_OUT";
  created_at: string;
  updated_at: string;
}

type StateFilter = "ALL" | "PENDING" | "REACHED_OUT";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);
  const [filter, setFilter] = useState<StateFilter>("ALL");

  const fetchLeads = useCallback(async () => {
    try {
      const data = await apiFetch<Lead[]>("/api/leads");
      setLeads(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  async function markReachedOut(id: string) {
    setUpdating(id);
    try {
      const updated = await apiFetch<Lead>(`/api/leads/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ state: "REACHED_OUT" }),
      });
      setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setUpdating(null);
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-stone-500">
        Loading leads…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={() => {
            setError("");
            setLoading(true);
            fetchLeads();
          }}
          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const filtered = filter === "ALL" ? leads : leads.filter((l) => l.state === filter);

  const counts = {
    ALL: leads.length,
    PENDING: leads.filter((l) => l.state === "PENDING").length,
    REACHED_OUT: leads.filter((l) => l.state === "REACHED_OUT").length,
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">Leads</h2>
          <p className="text-sm text-stone-500">
            {filtered.length} of {leads.length}{" "}
            {leads.length === 1 ? "lead" : "leads"}
            {filter !== "ALL" && " shown"}
          </p>
        </div>

        <div className="flex gap-1 rounded-lg border border-stone-200 bg-stone-50 p-1">
          {(["ALL", "PENDING", "REACHED_OUT"] as const).map((val) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === val
                  ? "bg-white text-stone-900 shadow-sm"
                  : "text-stone-500 hover:text-stone-700"
              }`}
            >
              {val === "ALL" ? "All" : val === "PENDING" ? "Pending" : "Reached Out"}
              <span className="ml-1.5 text-stone-400">{counts[val]}</span>
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-stone-200 bg-white py-12 text-center text-sm text-stone-500">
          {leads.length === 0
            ? "No leads yet."
            : "No leads match this filter."}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-stone-200">
            <thead className="bg-stone-50">
              <tr>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Name
                </th>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Email
                </th>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Submitted
                </th>
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  State
                </th>
                <th className="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wide text-stone-500">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filtered.map((lead, i) => (
                <tr
                  key={lead.id}
                  className={`${i % 2 === 1 ? "bg-stone-50/50" : ""} hover:bg-stone-50`}
                >
                  <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-stone-900">
                    {lead.first_name} {lead.last_name}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-sm text-stone-600">
                    {lead.email}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-sm text-stone-500">
                    {formatDate(lead.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4">
                    <StateBadge state={lead.state} />
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-right">
                    {lead.state === "PENDING" ? (
                      <button
                        onClick={() => markReachedOut(lead.id)}
                        disabled={updating === lead.id}
                        className="rounded-md border border-indigo-300 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 disabled:opacity-50"
                      >
                        {updating === lead.id
                          ? "Updating…"
                          : "Mark Reached Out"}
                      </button>
                    ) : (
                      <span className="text-xs text-stone-400">—</span>
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

function StateBadge({ state }: { state: "PENDING" | "REACHED_OUT" }) {
  const styles =
    state === "PENDING"
      ? "bg-amber-50 text-amber-700 ring-amber-200"
      : "bg-emerald-50 text-emerald-700 ring-emerald-200";

  const label = state === "PENDING" ? "Pending" : "Reached Out";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles}`}
    >
      {label}
    </span>
  );
}
