import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../lib/api";

interface ReachedOutBy {
  id: string;
  email: string;
}

interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  resume_path: string;
  state: "PENDING" | "REACHED_OUT";
  created_at: string;
  updated_at: string;
  reached_out_at: string | null;
  reached_out_by: ReachedOutBy | null;
}

interface LeadListResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

type StateFilter = "ALL" | "PENDING" | "REACHED_OUT";

const PAGE_SIZE = 50;

export default function LeadsPage() {
  const [data, setData] = useState<LeadListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);
  const [filter, setFilter] = useState<StateFilter>("ALL");
  const [page, setPage] = useState(0);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filter !== "ALL") params.set("state", filter);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(page * PAGE_SIZE));
      const qs = params.toString();
      const res = await apiFetch<LeadListResponse>(`/api/leads?${qs}`);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [filter, page]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  function handleFilterChange(f: StateFilter) {
    setFilter(f);
    setPage(0);
  }

  async function markReachedOut(id: string) {
    setUpdating(id);
    try {
      const updated = await apiFetch<Lead>(`/api/leads/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ state: "REACHED_OUT" }),
      });
      setData((prev) =>
        prev
          ? { ...prev, items: prev.items.map((l) => (l.id === id ? updated : l)) }
          : prev
      );
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

  const leads = data?.items ?? [];
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-stone-500">
        Loading leads…
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={() => {
            setError("");
            fetchLeads();
          }}
          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">Leads</h2>
          <p className="text-sm text-stone-500">
            {data ? `${data.total} ${data.total === 1 ? "lead" : "leads"}` : "Loading..."}
          </p>
        </div>

        <div className="flex gap-1 rounded-lg border border-stone-200 bg-stone-50 p-1">
          {(["ALL", "PENDING", "REACHED_OUT"] as const).map((val) => (
            <button
              key={val}
              onClick={() => handleFilterChange(val)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === val
                  ? "bg-white text-stone-900 shadow-sm"
                  : "text-stone-500 hover:text-stone-700"
              }`}
            >
              {val === "ALL" ? "All" : val === "PENDING" ? "Pending" : "Reached Out"}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button
            onClick={() => { setError(""); fetchLeads(); }}
            className="ml-2 font-medium underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {leads.length === 0 ? (
        <div className="rounded-lg border border-stone-200 bg-white py-12 text-center text-sm text-stone-500">
          {filter === "ALL" ? "No leads yet." : "No leads match this filter."}
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
                <th className="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                  Reached Out By
                </th>
                <th className="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wide text-stone-500">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {leads.map((lead, i) => (
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
                  <td className="whitespace-nowrap px-5 py-4 text-sm text-stone-500">
                    {lead.reached_out_by ? (
                      <span title={lead.reached_out_at ? formatDate(lead.reached_out_at) : undefined}>
                        {lead.reached_out_by.email}
                      </span>
                    ) : (
                      <span className="text-stone-300">—</span>
                    )}
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

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-stone-500">
            Page {page + 1} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-md border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-md border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-40"
            >
              Next
            </button>
          </div>
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
