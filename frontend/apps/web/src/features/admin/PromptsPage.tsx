import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, Plus, ScrollText, Trash2 } from "lucide-react";
import {
  useAdminPromptsList,
  useAdminPromptsCreate,
  useAdminPromptsActivate,
  useAdminPromptsDelete,
  getAdminPromptsListQueryKey,
} from "@/api/generated/endpoints/admin/admin";
import type { PromptResponse } from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/design";
import { cn } from "@/lib/utils";

export default function PromptsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useAdminPromptsList();
  const [newOpen, setNewOpen] = useState(false);
  const [presetName, setPresetName] = useState<string | undefined>();

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: getAdminPromptsListQueryKey() });

  const grouped = useMemo(() => {
    const map = new Map<string, PromptResponse[]>();
    for (const p of data?.items ?? []) {
      const arr = map.get(p.name) ?? [];
      arr.push(p);
      map.set(p.name, arr);
    }
    for (const arr of map.values()) arr.sort((a, b) => b.version - a.version);
    return [...map.entries()];
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Versioned prompts. Activating a version atomically retires the prior
          active one for the same name.
        </p>
        <Button
          onClick={() => {
            setPresetName(undefined);
            setNewOpen(true);
          }}
        >
          <Plus className="size-3.5" strokeWidth={1.5} />
          New prompt
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : grouped.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="No prompts yet"
          description="Create the named prompts the pipeline reads (extraction.system, judge.rubric, …)."
        />
      ) : (
        <div className="space-y-4">
          {grouped.map(([name, versions]) => (
            <PromptGroup
              key={name}
              name={name}
              versions={versions}
              onChanged={invalidate}
              onNewVersion={() => {
                setPresetName(name);
                setNewOpen(true);
              }}
            />
          ))}
        </div>
      )}

      <NewPromptDialog
        open={newOpen}
        onOpenChange={setNewOpen}
        presetName={presetName}
        onCreated={invalidate}
      />
    </div>
  );
}

function PromptGroup({
  name,
  versions,
  onChanged,
  onNewVersion,
}: {
  name: string;
  versions: PromptResponse[];
  onChanged: () => void;
  onNewVersion: () => void;
}) {
  const activate = useAdminPromptsActivate();
  const del = useAdminPromptsDelete();
  const [selectedId, setSelectedId] = useState(versions[0].id);
  const selected = versions.find((v) => v.id === selectedId) ?? versions[0];

  const doActivate = () => {
    activate.mutate(
      { promptId: selected.id },
      {
        onSuccess: () => {
          toast.success(`v${selected.version} activated`);
          onChanged();
        },
        onError: () => toast.error("Activation failed"),
      },
    );
  };

  const doDelete = () => {
    if (!confirm(`Delete ${name} v${selected.version}?`)) return;
    del.mutate(
      { promptId: selected.id },
      {
        onSuccess: () => {
          toast.success("Version deleted");
          onChanged();
        },
        onError: () => toast.error("Could not delete (active versions cannot be removed)"),
      },
    );
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ScrollText className="size-4 text-muted-foreground" strokeWidth={1.5} />
          <span className="font-mono text-sm font-medium text-foreground">
            {name}
          </span>
          <span className="text-xs text-muted-foreground">
            ({versions.length} version{versions.length > 1 ? "s" : ""})
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={onNewVersion}>
          <Plus className="size-3.5" strokeWidth={1.5} />
          New version
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {versions.map((v) => (
          <button
            key={v.id}
            onClick={() => setSelectedId(v.id)}
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors",
              v.id === selectedId
                ? "bg-primary text-primary-foreground"
                : "border border-border bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            v{v.version}
            {v.is_active && <Check className="size-3" strokeWidth={2} />}
          </button>
        ))}
      </div>

      <div className="mt-3">
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline">{selected.role}</Badge>
          {selected.model_hint && <span>hint: {selected.model_hint}</span>}
          {selected.is_active && <Badge variant="default">active</Badge>}
          <span className="ml-auto">
            {new Date(selected.created_at).toLocaleString()}
          </span>
        </div>
        <pre className="max-h-64 overflow-auto rounded-lg border border-border bg-muted/40 p-3 text-xs whitespace-pre-wrap text-foreground">
          {selected.content}
        </pre>
      </div>

      <div className="mt-3 flex items-center justify-end gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={doDelete}
          disabled={del.isPending || selected.is_active}
        >
          <Trash2 className="size-3.5 text-destructive" strokeWidth={1.5} />
        </Button>
        <Button
          size="sm"
          onClick={doActivate}
          disabled={activate.isPending || selected.is_active}
        >
          <Check className="size-3.5" strokeWidth={1.5} />
          Activate
        </Button>
      </div>
    </div>
  );
}

function NewPromptDialog({
  open,
  onOpenChange,
  presetName,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  presetName?: string;
  onCreated: () => void;
}) {
  const create = useAdminPromptsCreate();
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [role, setRole] = useState("system");
  const [activateNow, setActivateNow] = useState(true);

  const effectiveName = presetName ?? name;

  const submit = () => {
    create.mutate(
      {
        data: {
          name: effectiveName.trim(),
          content,
          role,
          activate: activateNow,
        },
      },
      {
        onSuccess: () => {
          toast.success("Prompt version created");
          setName("");
          setContent("");
          onOpenChange(false);
          onCreated();
        },
        onError: () => toast.error("Could not create prompt"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {presetName ? `New version of ${presetName}` : "New prompt"}
          </DialogTitle>
          <DialogDescription>
            A new version is created. Optionally activate it immediately.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {!presetName && (
            <div className="space-y-1.5">
              <Label htmlFor="pname">Name</Label>
              <Input
                id="pname"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="extraction.system"
                className="font-mono"
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              />
            </div>
            <label className="flex items-end gap-2 pb-2 text-sm">
              <input
                type="checkbox"
                checked={activateNow}
                onChange={(e) => setActivateNow(e.target.checked)}
              />
              Activate immediately
            </label>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={12}
              className="font-mono text-xs"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={
              create.isPending || !effectiveName.trim() || content.length < 1
            }
          >
            Create version
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
