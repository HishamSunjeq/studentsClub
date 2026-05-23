import { useState } from "react";
import { Activity } from "lucide-react";
import {
  useAdminAiRunsList,
  useAdminAiRunsGet,
} from "@/api/generated/endpoints/admin/admin";
import type { AIRunResponse } from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/design";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  succeeded: "bg-[color:var(--success)]/10 text-[color:var(--success)]",
  failed: "bg-destructive/10 text-destructive",
  running: "bg-primary/10 text-primary",
};

const PAGE_SIZE = 50;

export default function AIRunsPage() {
  const [page, setPage] = useState(1);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);

  const { data, isLoading } = useAdminAiRunsList({
    page,
    size: PAGE_SIZE,
    provider: provider || undefined,
    model: model || undefined,
    status: statusFilter || undefined,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Rollup over the filtered set */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Runs" value={total.toLocaleString()} />
        <Stat
          label="Cost"
          value={`$${Number(data?.total_cost_usd ?? 0).toFixed(4)}`}
        />
        <Stat
          label="Input tokens"
          value={(data?.total_input_tokens ?? 0).toLocaleString()}
        />
        <Stat
          label="Output tokens"
          value={(data?.total_output_tokens ?? 0).toLocaleString()}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <Input
          placeholder="provider"
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value);
            setPage(1);
          }}
          className="w-40"
        />
        <Input
          placeholder="model"
          value={model}
          onChange={(e) => {
            setModel(e.target.value);
            setPage(1);
          }}
          className="w-48"
        />
        <Input
          placeholder="status"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="w-36"
        />
      </div>

      {isLoading ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No runs match"
          description="Telemetry rows appear here as the pipeline executes provider calls."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2.5 text-left font-medium">Time</th>
                <th className="px-3 py-2.5 text-left font-medium">Task</th>
                <th className="px-3 py-2.5 text-left font-medium">Model</th>
                <th className="px-3 py-2.5 text-right font-medium">Tokens</th>
                <th className="px-3 py-2.5 text-right font-medium">Cost</th>
                <th className="px-3 py-2.5 text-right font-medium">Latency</th>
                <th className="px-3 py-2.5 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setDetailId(r.id)}
                  className="cursor-pointer hover:bg-muted/30"
                >
                  <td className="px-3 py-2.5 whitespace-nowrap text-muted-foreground">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2.5 text-foreground">{r.task_name}</td>
                  <td className="px-3 py-2.5 text-muted-foreground">
                    {r.provider}/{r.model}
                    {r.cache_hit && (
                      <Badge variant="secondary" className="ml-1.5">
                        cache
                      </Badge>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-muted-foreground">
                    {r.input_tokens}/{r.output_tokens}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-muted-foreground">
                    ${Number(r.cost_usd).toFixed(4)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-muted-foreground">
                    {r.latency_ms != null ? `${r.latency_ms}ms` : "—"}
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                        STATUS_STYLES[r.status] ??
                          "bg-muted text-muted-foreground",
                      )}
                    >
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      <RunDetailDialog runId={detailId} onClose={() => setDetailId(null)} />
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

function RunDetailDialog({
  runId,
  onClose,
}: {
  runId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useAdminAiRunsGet(runId ?? "", {
    query: { enabled: !!runId },
  });

  return (
    <Dialog open={!!runId} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Run detail</DialogTitle>
        </DialogHeader>
        {isLoading || !data ? (
          <Skeleton className="h-64" />
        ) : (
          <div className="space-y-3 text-sm">
            <Field k="Task" v={data.task_name} />
            <Field k="Model" v={`${data.provider}/${data.model}`} />
            <Field k="Credential" v={data.credential_alias ?? "—"} />
            <Field
              k="Tokens"
              v={`${data.input_tokens} in / ${data.output_tokens} out`}
            />
            <Field k="Cost" v={`$${Number(data.cost_usd).toFixed(6)}`} />
            <Field
              k="Latency"
              v={data.latency_ms != null ? `${data.latency_ms}ms` : "—"}
            />
            <Field k="Status" v={data.status} />
            {data.parent_run_id && (
              <Field k="Parent run" v={data.parent_run_id} />
            )}
            {data.error && (
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground">
                  Error
                </p>
                <pre className="mt-1 overflow-auto rounded-lg bg-destructive/10 p-3 text-xs text-destructive">
                  {data.error}
                </pre>
              </div>
            )}
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Metadata
              </p>
              <pre className="mt-1 max-h-64 overflow-auto rounded-lg border border-border bg-muted/40 p-3 text-xs whitespace-pre-wrap">
                {JSON.stringify(data.meta ?? {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Field({ k, v }: { k: string; v: AIRunResponse[keyof AIRunResponse] }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border pb-2">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">
        {k}
      </span>
      <span className="font-mono text-foreground">{String(v)}</span>
    </div>
  );
}
