import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, SlidersHorizontal, Star } from "lucide-react";
import {
  useAdminProfilesList,
  useAdminProfilesCreate,
  useAdminProfilesUpdate,
  useAdminProfilesDelete,
  useAdminModelsList,
  useAdminCredentialsList,
  getAdminProfilesListQueryKey,
} from "@/api/generated/endpoints/admin/admin";
import type {
  ProfileResponse,
  ProfileUpdateRequest,
  ModelResponse,
  CredentialResponse,
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

const NONE = "__none__";

export default function ProfilesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useAdminProfilesList();
  const { data: modelsData } = useAdminModelsList();
  const { data: credsData } = useAdminCredentialsList();
  const create = useAdminProfilesCreate();
  const del = useAdminProfilesDelete();
  const [editing, setEditing] = useState<ProfileResponse | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: getAdminProfilesListQueryKey() });

  const items = data?.items ?? [];
  const models = modelsData?.items ?? [];
  const creds = credsData?.items ?? [];

  const addProfile = () => {
    create.mutate(
      { data: { name: "New profile" } },
      {
        onSuccess: (row) => {
          toast.success("Profile created");
          invalidate();
          setEditing(row);
        },
        onError: () => toast.error("Could not create profile"),
      },
    );
  };

  const removeProfile = (p: ProfileResponse) => {
    if (!confirm(`Delete profile "${p.name}"?`)) return;
    del.mutate(
      { profileId: p.id },
      {
        onSuccess: () => {
          toast.success("Profile deleted");
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
          Per-subject (or global default) generation behavior: which models,
          credentials, thresholds, and retrieval settings to use.
        </p>
        <Button onClick={addProfile} disabled={create.isPending}>
          <Plus className="size-3.5" strokeWidth={1.5} />
          New profile
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={SlidersHorizontal}
          title="No profiles yet"
          description="Create a global default profile to control how question sets are generated."
        />
      ) : (
        <div className="space-y-3">
          {items.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between rounded-xl border border-border bg-card p-5"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{p.name}</span>
                  {p.is_default && (
                    <Badge variant="default">
                      <Star className="size-3" strokeWidth={2} /> default
                    </Badge>
                  )}
                  <Badge variant="outline">
                    {p.subject_id ? "subject" : "global"}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  target {p.target_count} · judge ≥ {p.judge_threshold} · dedup{" "}
                  {p.dedup_threshold} · top-k {p.top_k_retrieval} → top-n{" "}
                  {p.top_n_rerank}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditing(p)}
                >
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeProfile(p)}
                  disabled={del.isPending}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <EditProfileDialog
        profile={editing}
        models={models}
        credentials={creds}
        onClose={() => setEditing(null)}
        onSaved={invalidate}
      />
    </div>
  );
}

function EditProfileDialog({
  profile,
  models,
  credentials,
  onClose,
  onSaved,
}: {
  profile: ProfileResponse | null;
  models: ModelResponse[];
  credentials: CredentialResponse[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const update = useAdminProfilesUpdate();
  const [draft, setDraft] = useState<ProfileUpdateRequest>({});

  // Re-seed local draft when a new profile opens.
  const [seededId, setSeededId] = useState<string | null>(null);
  if (profile && profile.id !== seededId) {
    setSeededId(profile.id);
    setDraft({
      name: profile.name,
      target_count: profile.target_count,
      judge_threshold: profile.judge_threshold,
      dedup_threshold: profile.dedup_threshold,
      top_k_retrieval: profile.top_k_retrieval,
      top_n_rerank: profile.top_n_rerank,
      hybrid_alpha: profile.hybrid_alpha,
      extraction_model_id: profile.extraction_model_id,
      judge_model_id: profile.judge_model_id,
      embedding_model_id: profile.embedding_model_id,
      rerank_model_id: profile.rerank_model_id,
      credential_alias_extraction: profile.credential_alias_extraction,
      credential_alias_judge: profile.credential_alias_judge,
      credential_alias_embedding: profile.credential_alias_embedding,
      credential_alias_rerank: profile.credential_alias_rerank,
      is_default: profile.is_default,
    });
  }

  const set = <K extends keyof ProfileUpdateRequest>(
    k: K,
    v: ProfileUpdateRequest[K],
  ) => setDraft((d) => ({ ...d, [k]: v }));

  const save = () => {
    if (!profile) return;
    update.mutate(
      { profileId: profile.id, data: draft },
      {
        onSuccess: () => {
          toast.success("Profile saved");
          onClose();
          onSaved();
        },
        onError: () => toast.error("Save failed (check model references)"),
      },
    );
  };

  const modelsByKind = (kind: string) =>
    models.filter((m) => m.kind === kind && m.is_active);

  return (
    <Dialog open={!!profile} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit profile</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="pname">Name</Label>
            <Input
              id="pname"
              value={draft.name ?? ""}
              onChange={(e) => set("name", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <ModelSelect
              label="Extraction model"
              value={draft.extraction_model_id ?? null}
              options={modelsByKind("extraction").concat(modelsByKind("chat"))}
              onChange={(v) => set("extraction_model_id", v)}
            />
            <ModelSelect
              label="Judge model"
              value={draft.judge_model_id ?? null}
              options={modelsByKind("judge").concat(modelsByKind("chat"))}
              onChange={(v) => set("judge_model_id", v)}
            />
            <ModelSelect
              label="Embedding model"
              value={draft.embedding_model_id ?? null}
              options={modelsByKind("embedding")}
              onChange={(v) => set("embedding_model_id", v)}
            />
            <ModelSelect
              label="Rerank model"
              value={draft.rerank_model_id ?? null}
              options={modelsByKind("rerank")}
              onChange={(v) => set("rerank_model_id", v)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <CredSelect
              label="Credential — extraction"
              value={draft.credential_alias_extraction ?? null}
              credentials={credentials}
              onChange={(v) => set("credential_alias_extraction", v)}
            />
            <CredSelect
              label="Credential — judge"
              value={draft.credential_alias_judge ?? null}
              credentials={credentials}
              onChange={(v) => set("credential_alias_judge", v)}
            />
            <CredSelect
              label="Credential — embedding"
              value={draft.credential_alias_embedding ?? null}
              credentials={credentials}
              onChange={(v) => set("credential_alias_embedding", v)}
            />
            <CredSelect
              label="Credential — rerank"
              value={draft.credential_alias_rerank ?? null}
              credentials={credentials}
              onChange={(v) => set("credential_alias_rerank", v)}
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <NumField
              label="Target count"
              value={draft.target_count}
              onChange={(v) => set("target_count", v)}
            />
            <NumField
              label="Judge threshold"
              value={draft.judge_threshold}
              onChange={(v) => set("judge_threshold", v)}
              step="0.1"
            />
            <NumField
              label="Dedup threshold"
              value={draft.dedup_threshold}
              onChange={(v) => set("dedup_threshold", v)}
              step="0.01"
            />
            <NumField
              label="Top-k retrieval"
              value={draft.top_k_retrieval}
              onChange={(v) => set("top_k_retrieval", v)}
            />
            <NumField
              label="Top-n rerank"
              value={draft.top_n_rerank}
              onChange={(v) => set("top_n_rerank", v)}
            />
            <NumField
              label="Hybrid alpha"
              value={draft.hybrid_alpha}
              onChange={(v) => set("hybrid_alpha", v)}
              step="0.05"
            />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!draft.is_default}
              onChange={(e) => set("is_default", e.target.checked)}
            />
            Default profile for this scope
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={update.isPending}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ModelSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | null;
  options: ModelResponse[];
  onChange: (v: string | null) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select
        value={value ?? NONE}
        onValueChange={(v) => onChange(v === NONE ? null : v)}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="None" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>None</SelectItem>
          {options.map((m) => (
            <SelectItem key={m.id} value={m.id}>
              {m.display_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function CredSelect({
  label,
  value,
  credentials,
  onChange,
}: {
  label: string;
  value: string | null;
  credentials: CredentialResponse[];
  onChange: (v: string | null) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select
        value={value ?? NONE}
        onValueChange={(v) => onChange(v === NONE ? null : v)}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Default" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>Default</SelectItem>
          {credentials.map((c) => (
            <SelectItem key={c.id} value={c.alias}>
              {c.alias} ({c.provider})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function NumField({
  label,
  value,
  onChange,
  step,
}: {
  label: string;
  value: number | string | null | undefined;
  onChange: (v: number) => void;
  step?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        type="number"
        step={step}
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
