import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { useAdminAiMetricsGet } from "@/api/generated/endpoints/admin/admin";
import type {
  MetricPoint,
  MetricsBreakdownRow,
} from "@/api/generated/schemas";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const RANGES = [7, 30, 90];

export default function AIDashboardPage() {
  const [range, setRange] = useState(30);
  const { data, isLoading, error } = useAdminAiMetricsGet({ range });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={cn(
              "rounded-full px-4 py-1.5 text-xs font-medium transition-colors",
              range === r
                ? "bg-primary text-primary-foreground"
                : "border border-border bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {r}d
          </button>
        ))}
      </div>

      {error ? (
        <div className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-5 text-sm">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
          <div className="space-y-1">
            <p className="font-medium text-destructive">
              Failed to load AI metrics
            </p>
            <p className="text-muted-foreground">
              The metrics endpoint returned an error. Telemetry may be empty,
              or the aggregation query failed — check API logs.
            </p>
          </div>
        </div>
      ) : isLoading || !data ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat
              label="Total cost"
              value={`$${Number(data.total_cost_usd).toFixed(2)}`}
            />
            <Stat label="Calls" value={data.total_calls.toLocaleString()} />
            <Stat
              label="Cache hit rate"
              value={`${(data.cache_hit_rate * 100).toFixed(1)}%`}
            />
            <Stat
              label="Latency p50 / p95"
              value={`${data.p50_latency_ms ?? "—"} / ${data.p95_latency_ms ?? "—"}ms`}
            />
          </div>

          <Panel title="Daily cost (USD)">
            <Bars points={data.daily} pick={(d) => Number(d.cost_usd)} />
          </Panel>

          <Panel title="Daily calls">
            <Bars points={data.daily} pick={(d) => d.calls} />
          </Panel>

          <div className="grid gap-4 lg:grid-cols-3">
            <Breakdown title="By provider" rows={data.by_provider} />
            <Breakdown title="By model" rows={data.by_model} />
            <Breakdown title="By credential" rows={data.by_credential} />
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold text-foreground">{value}</p>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-4 text-sm font-medium text-foreground">{title}</p>
      {children}
    </div>
  );
}

function Bars({
  points,
  pick,
}: {
  points: MetricPoint[];
  pick: (d: MetricPoint) => number;
}) {
  if (points.length === 0) {
    return <p className="text-sm text-muted-foreground">No data in range.</p>;
  }
  const max = Math.max(...points.map(pick), 1e-9);
  return (
    <div className="flex h-40 items-end gap-1">
      {points.map((d) => {
        const v = pick(d);
        const h = Math.max(2, (v / max) * 100);
        return (
          <div
            key={d.day}
            className="group relative flex-1"
            title={`${d.day}: ${v.toLocaleString()}`}
          >
            <div
              className="rounded-t bg-primary/70 transition-colors group-hover:bg-primary"
              style={{ height: `${h}%` }}
            />
          </div>
        );
      })}
    </div>
  );
}

function Breakdown({
  title,
  rows,
}: {
  title: string;
  rows: MetricsBreakdownRow[];
}) {
  const max = Math.max(...rows.map((r) => Number(r.cost_usd)), 1e-9);
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-3 text-sm font-medium text-foreground">{title}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No data.</p>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.key}>
              <div className="flex justify-between text-xs">
                <span className="truncate text-foreground">{r.key}</span>
                <span className="font-mono text-muted-foreground">
                  ${Number(r.cost_usd).toFixed(2)}
                </span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary/70"
                  style={{ width: `${(Number(r.cost_usd) / max) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
