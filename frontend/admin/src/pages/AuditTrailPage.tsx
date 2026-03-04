import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../lib/api";

interface AuditEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_id: string | null;
  user_email: string | null;
  old_state: string | null;
  new_state: string | null;
  detail: string | null;
  lead_id: string | null;
  created_at: string;
}

interface AuditResponse {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

type EntityFilter = "all" | "lead" | "user";

const ACTION_LABELS: Record<string, string> = {
  lead_created: "Lead Created",
  state_change: "State Change",
  attorney_created: "Attorney Created",
  user_deactivated: "User Deactivated",
  user_reactivated: "User Reactivated",
  user_deleted: "User Deleted",
  user_registered: "User Registered",
  user_login: "User Login",
};

const ACTION_STYLES: Record<string, string> = {
  lead_created: "bg-blue-50 text-blue-700 ring-blue-200",
  state_change: "bg-violet-50 text-violet-700 ring-violet-200",
  attorney_created: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  user_deactivated: "bg-red-50 text-red-700 ring-red-200",
  user_reactivated: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  user_deleted: "bg-red-50 text-red-700 ring-red-200",
  user_registered: "bg-sky-50 text-sky-700 ring-sky-200",
  user_login: "bg-stone-100 text-stone-600 ring-stone-200",
};

const PAGE_SIZE = 25;

export default function AuditTrailPage() {
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [entityFilter, setEntityFilter] = useState<EntityFilter>("all");
  const [page, setPage] = useState(0);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (entityFilter !== "all") params.set("entity_type", entityFilter);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(page * PAGE_SIZE));
      const qs = params.toString();
      const res = await apiFetch<AuditResponse>(`/api/admin/audit-logs?${qs}`);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [entityFilter, page]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  function handleFilterChange(f: EntityFilter) {
    setEntityFilter(f);
    setPage(0);
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-800">Audit Trail</h2>
          <p className="text-sm text-stone-500">
            {data
              ? `${data.total} ${data.total === 1 ? "entry" : "entries"}`
              : "Loading..."}
          </p>
        </div>

        <div className="flex gap-1 rounded-lg border border-stone-200 bg-stone-50 p-1">
          {(["all", "lead", "user"] as const).map((val) => (
            <button
              key={val}
              onClick={() => handleFilterChange(val)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                entityFilter === val
                  ? "bg-white text-stone-900 shadow-sm"
                  : "text-stone-500 hover:text-stone-700"
              }`}
            >
              {val === "all" ? "All" : val === "lead" ? "Leads" : "Users"}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button
            onClick={() => {
              setError("");
              fetchLogs();
            }}
            className="ml-2 font-medium underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {loading && !data ? (
        <div className="flex items-center justify-center py-20 text-sm text-stone-500">
          Loading audit logs...
        </div>
      ) : data && data.items.length === 0 ? (
        <div className="rounded-lg border border-stone-200 bg-white py-12 text-center text-sm text-stone-500">
          No audit entries found.
        </div>
      ) : data ? (
        <>
          <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-stone-200">
              <thead className="bg-stone-50">
                <tr>
                  <th className="px-4 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                    When
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                    Action
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                    Entity
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                    By
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-medium uppercase tracking-wide text-stone-500">
                    Detail
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.items.map((entry, i) => (
                  <tr
                    key={entry.id}
                    className={`${
                      i % 2 === 1 ? "bg-stone-50/50" : ""
                    } hover:bg-stone-50`}
                  >
                    <td className="whitespace-nowrap px-4 py-3.5 text-xs text-stone-500">
                      {formatDate(entry.created_at)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5">
                      <ActionBadge action={entry.action} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5">
                      <span className="inline-flex items-center gap-1.5 text-xs text-stone-600">
                        <EntityIcon type={entry.entity_type} />
                        <span className="font-medium capitalize">
                          {entry.entity_type}
                        </span>
                        <span className="font-mono text-[10px] text-stone-400">
                          {entry.entity_id.slice(0, 8)}
                        </span>
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-xs text-stone-600">
                      {entry.user_email ?? (
                        <span className="italic text-stone-400">public</span>
                      )}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3.5 text-xs text-stone-500">
                      {entry.old_state && entry.new_state ? (
                        <span>
                          <span className="font-medium text-stone-600">
                            {entry.old_state}
                          </span>
                          {" → "}
                          <span className="font-medium text-stone-600">
                            {entry.new_state}
                          </span>
                        </span>
                      ) : (
                        entry.detail ?? "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
                  onClick={() =>
                    setPage((p) => Math.min(totalPages - 1, p + 1))
                  }
                  disabled={page >= totalPages - 1}
                  className="rounded-md border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const styles =
    ACTION_STYLES[action] ?? "bg-stone-100 text-stone-600 ring-stone-200";
  const label = ACTION_LABELS[action] ?? action.replace(/_/g, " ");

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset capitalize ${styles}`}
    >
      {label}
    </span>
  );
}

function EntityIcon({ type }: { type: string }) {
  if (type === "lead") {
    return (
      <svg
        className="h-3.5 w-3.5 text-stone-400"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
        />
      </svg>
    );
  }
  return (
    <svg
      className="h-3.5 w-3.5 text-stone-400"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
      />
    </svg>
  );
}
