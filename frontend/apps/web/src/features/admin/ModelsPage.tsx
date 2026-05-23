import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Cpu, Plus, Trash2 } from "lucide-react";
import {
  useAdminModelsList,
  useAdminModelsCreate,
  useAdminModelsUpdate,
  useAdminModelsDelete,
  getAdminModelsListQueryKey,
} from "@/api/generated/endpoints/admin/admin";
import {
  ModelCreateRequestKind,
  type ModelResponse,
} from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/design";

const KINDS = Object.values(ModelCreateRequestKind);

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useAdminModelsList();
  const update = useAdminModelsUpdate();
  const del = useAdminModelsDelete();
  const [addOpen, setAddOpen] = useState(false);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: getAdminModelsListQueryKey() });

  const items = data?.items ?? [];

  const toggleActive = (m: ModelResponse) => {
    update.mutate(
      { modelId: m.id, data: { is_active: !m.is_active } },
      {
        onSuccess: () => {
          toast.success(m.is_active ? "Model disabled" : "Model enabled");
          invalidate();
        },
        onError: () => toast.error("Update failed"),
      },
    );
  };

  const runDelete = (m: ModelResponse) => {
    if (!confirm(`Delete model ${m.provider}/${m.model_id}?`)) return;
    del.mutate(
      { modelId: m.id },
      {
        onSuccess: () => {
          toast.success("Model deleted");
          invalidate();
        },
        onError: () => toast.error("Delete failed"),
      },
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Models the orchestrator can use. Pricing here drives the cost figures
          in telemetry.
        </p>
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="size-3.5" strokeWidth={1.5} />
          Add model
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Cpu}
          title="No models registered"
          description="Add the models your profiles will reference for extraction, judging, embedding, and reranking."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Model</th>
                <th className="px-4 py-2.5 text-left font-medium">Kind</th>
                <th className="px-4 py-2.5 text-left font-medium">Context</th>
                <th className="px-4 py-2.5 text-left font-medium">
                  $/Mtok in·out
                </th>
                <th className="px-4 py-2.5 text-left font-medium">Active</th>
                <th className="px-4 py-2.5 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((m) => (
                <tr key={m.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">
                      {m.display_name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {m.provider} / {m.model_id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="capitalize">
                      {m.kind}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {m.context_window
                      ? `${(m.context_window / 1000).toFixed(0)}k`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">
                    {m.input_cost_per_mtoken}·{m.output_cost_per_mtoken}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive(m)}
                      disabled={update.isPending}
                      className="text-left"
                    >
                      <Badge variant={m.is_active ? "default" : "secondary"}>
                        {m.is_active ? "active" : "inactive"}
                      </Badge>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => runDelete(m)}
                      disabled={del.isPending}
                    >
                      <Trash2
                        className="size-3.5 text-destructive"
                        strokeWidth={1.5}
                      />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddModelDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onCreated={invalidate}
      />
    </div>
  );
}

function AddModelDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCreated: () => void;
}) {
  const create = useAdminModelsCreate();
  const [provider, setProvider] = useState("openai");
  const [modelId, setModelId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [kind, setKind] = useState<string>(KINDS[0]);
  const [contextWindow, setContextWindow] = useState("");
  const [inCost, setInCost] = useState("");
  const [outCost, setOutCost] = useState("");

  const submit = () => {
    create.mutate(
      {
        data: {
          provider: provider.trim(),
          model_id: modelId.trim(),
          display_name: displayName.trim() || modelId.trim(),
          kind: kind as ModelCreateRequestKind,
          context_window: contextWindow ? Number(contextWindow) : undefined,
          input_cost_per_mtoken: inCost ? Number(inCost) : undefined,
          output_cost_per_mtoken: outCost ? Number(outCost) : undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Model added");
          onOpenChange(false);
          setModelId("");
          setDisplayName("");
          setContextWindow("");
          setInCost("");
          setOutCost("");
          onCreated();
        },
        onError: () => toast.error("Could not add model"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add model</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="provider">Provider</Label>
              <Input
                id="provider"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Kind</Label>
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KINDS.map((k) => (
                    <SelectItem key={k} value={k} className="capitalize">
                      {k}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="model_id">Model ID</Label>
            <Input
              id="model_id"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              placeholder="claude-opus-4-7"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="display">Display name (optional)</Label>
            <Input
              id="display"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="ctx">Context</Label>
              <Input
                id="ctx"
                type="number"
                value={contextWindow}
                onChange={(e) => setContextWindow(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="incost">$/Mtok in</Label>
              <Input
                id="incost"
                type="number"
                value={inCost}
                onChange={(e) => setInCost(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="outcost">$/Mtok out</Label>
              <Input
                id="outcost"
                type="number"
                value={outCost}
                onChange={(e) => setOutCost(e.target.value)}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={create.isPending || !modelId.trim() || !provider.trim()}
          >
            Add model
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
