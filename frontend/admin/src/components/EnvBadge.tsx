import { getApiEnv } from "../lib/api";

const ENV_STYLES: Record<string, string> = {
  local: "bg-stone-200 text-stone-600",
  staging: "bg-amber-100 text-amber-700",
  prod: "bg-red-100 text-red-700",
};

export default function EnvBadge() {
  const env = getApiEnv();
  const style = ENV_STYLES[env] ?? ENV_STYLES.local;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ${style}`}
    >
      {env}
    </span>
  );
}
