import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { KeyRound, Plus, RotateCw, Trash2, Wand2 } from "lucide-react";
import {
  useAdminCredentialsList,
  useAdminCredentialsCreate,
  useAdminCredentialsRotate,
  useAdminCredentialsDelete,
  useAdminCredentialsTest,
  getAdminCredentialsListQueryKey,
} from "@/api/generated/endpoints/admin/admin";
import {
  CredentialCreateRequestProvider,
  type CredentialResponse,
} from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/design";

const PROVIDERS = Object.values(CredentialCreateRequestProvider);

export default function CredentialsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useAdminCredentialsList();
  const [addOpen, setAddOpen] = useState(false);
  const [rotateTarget, setRotateTarget] = useState<CredentialResponse | null>(
    null,
  );

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: getAdminCredentialsListQueryKey(),
    });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Keys are encrypted at rest. Only the last four characters are ever
          shown.
        </p>
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="size-3.5" strokeWidth={1.5} />
          Add credential
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={KeyRound}
          title="No credentials yet"
          description="Add a provider API key to start running generation through the admin-managed control plane."
          action={
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="size-3.5" strokeWidth={1.5} />
              Add credential
            </Button>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2.5 text-left font-medium">Alias</th>
                <th className="px-4 py-2.5 text-left font-medium">Provider</th>
                <th className="px-4 py-2.5 text-left font-medium">Key</th>
                <th className="px-4 py-2.5 text-left font-medium">Budget</th>
                <th className="px-4 py-2.5 text-left font-medium">Last used</th>
                <th className="px-4 py-2.5 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((c) => (
                <CredentialRow
                  key={c.id}
                  credential={c}
                  onRotate={() => setRotateTarget(c)}
                  onChanged={invalidate}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddCredentialDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onCreated={invalidate}
      />
      <RotateCredentialDialog
        credential={rotateTarget}
        onClose={() => setRotateTarget(null)}
        onRotated={invalidate}
      />
    </div>
  );
}

function CredentialRow({
  credential,
  onRotate,
  onChanged,
}: {
  credential: CredentialResponse;
  onRotate: () => void;
  onChanged: () => void;
}) {
  const test = useAdminCredentialsTest();
  const del = useAdminCredentialsDelete();

  const runTest = () => {
    test.mutate(
      { credentialId: credential.id },
      {
        onSuccess: (res) => {
          if (res.ok) {
            toast.success(
              `Key valid${res.latency_ms ? ` (${res.latency_ms}ms)` : ""}`,
            );
          } else {
            toast.error(res.detail ?? "Key check failed");
          }
        },
        onError: () => toast.error("Test request failed"),
      },
    );
  };

  const runDelete = () => {
    if (!confirm(`Revoke credential "${credential.alias}"?`)) return;
    del.mutate(
      { credentialId: credential.id },
      {
        onSuccess: () => {
          toast.success("Credential revoked");
          onChanged();
        },
        onError: () => toast.error("Could not revoke credential"),
      },
    );
  };

  return (
    <tr className="hover:bg-muted/30">
      <td className="px-4 py-3">
        <span className="font-medium text-foreground">{credential.alias}</span>
        {!credential.is_active && (
          <Badge variant="secondary" className="ml-2">
            inactive
          </Badge>
        )}
      </td>
      <td className="px-4 py-3 capitalize text-muted-foreground">
        {credential.provider}
      </td>
      <td className="px-4 py-3 font-mono text-muted-foreground">
        ••••{credential.key_last4}
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        {credential.monthly_budget_usd
          ? `$${credential.monthly_budget_usd}/mo`
          : "—"}
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        {credential.last_used_at
          ? new Date(credential.last_used_at).toLocaleDateString()
          : "never"}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={runTest}
            disabled={test.isPending}
          >
            <Wand2 className="size-3.5" strokeWidth={1.5} />
            Test
          </Button>
          <Button variant="ghost" size="sm" onClick={onRotate}>
            <RotateCw className="size-3.5" strokeWidth={1.5} />
            Rotate
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={runDelete}
            disabled={del.isPending}
          >
            <Trash2 className="size-3.5 text-destructive" strokeWidth={1.5} />
          </Button>
        </div>
      </td>
    </tr>
  );
}

function AddCredentialDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCreated: () => void;
}) {
  const create = useAdminCredentialsCreate();
  const [alias, setAlias] = useState("");
  const [provider, setProvider] = useState<string>(PROVIDERS[0]);
  const [apiKey, setApiKey] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [budget, setBudget] = useState("");

  const reset = () => {
    setAlias("");
    setProvider(PROVIDERS[0]);
    setApiKey("");
    setDisplayName("");
    setBudget("");
  };

  const submit = () => {
    create.mutate(
      {
        data: {
          alias: alias.trim(),
          provider: provider as CredentialCreateRequestProvider,
          api_key: apiKey,
          display_name: displayName.trim() || undefined,
          monthly_budget_usd: budget ? Number(budget) : undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success("Credential added");
          reset();
          onOpenChange(false);
          onCreated();
        },
        onError: () => toast.error("Could not add credential"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add credential</DialogTitle>
          <DialogDescription>
            The key is sent once over HTTPS, encrypted server-side, and never
            returned to the browser.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="alias">Alias</Label>
            <Input
              id="alias"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="openai-primary"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Provider</Label>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p} value={p} className="capitalize">
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="api_key">API key</Label>
            <Input
              id="api_key"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-…"
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
          <div className="space-y-1.5">
            <Label htmlFor="budget">Monthly budget USD (optional)</Label>
            <Input
              id="budget"
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="100"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={create.isPending || !alias.trim() || apiKey.length < 4}
          >
            Add credential
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RotateCredentialDialog({
  credential,
  onClose,
  onRotated,
}: {
  credential: CredentialResponse | null;
  onClose: () => void;
  onRotated: () => void;
}) {
  const rotate = useAdminCredentialsRotate();
  const [apiKey, setApiKey] = useState("");

  const submit = () => {
    if (!credential) return;
    rotate.mutate(
      { credentialId: credential.id, data: { api_key: apiKey } },
      {
        onSuccess: () => {
          toast.success("Key rotated");
          setApiKey("");
          onClose();
          onRotated();
        },
        onError: () => toast.error("Could not rotate key"),
      },
    );
  };

  return (
    <Dialog open={!!credential} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rotate key</DialogTitle>
          <DialogDescription>
            Replace the key for{" "}
            <span className="font-medium text-foreground">
              {credential?.alias}
            </span>{" "}
            without changing its alias. In-flight generations keep using the old
            key until they finish.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="new_key">New API key</Label>
          <Input
            id="new_key"
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-…"
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={rotate.isPending || apiKey.length < 4}
          >
            Rotate key
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
