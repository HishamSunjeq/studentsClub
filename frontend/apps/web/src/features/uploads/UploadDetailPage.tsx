import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import {
  getUploadsGetQueryKey,
  uploadsPreviewUrl,
  useUploadsDelete,
  useUploadsGenerate,
  useUploadsGenerationDefaults,
  useUploadsGet,
  useUploadsUpdate,
} from "@/api/generated/endpoints/uploads/uploads";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import type { GenerateRequest } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { Chip } from "@/components/design/Chip";
import { cn } from "@/lib/utils";
import {
  QS_STATUS_META,
  UPLOAD_STATUS_META,
  formatBytes,
} from "./status-meta";
import { useUploadEvents, type UploadEvent } from "./useUploadEvents";

const GENERATION_LS_KEY = "sc-upload-generation-settings";

type GenerationSettings = {
  count: number;
  difficulty_mix: { easy: number; medium: number; hard: number };
  question_types: string[];
  language: string;
  extraction_model_id?: string | null;
  profile_id?: string | null;
};

const DEFAULT_SETTINGS: GenerationSettings = {
  count: 10,
  difficulty_mix: { easy: 30, medium: 50, hard: 20 },
  question_types: ["mcq"],
  language: "en",
};

export default function UploadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const { data: upload, isLoading } = useUploadsGet(id ?? "", {
    query: {
      enabled: !!user && !!id,
      // SSE drives live generation progress; polling is a fallback. Poll fast
      // during extraction (no events emitted there), slow during generation.
      refetchInterval: (query) => {
        const u = query.state.data;
        if (!u) return false;
        if (u.status === "extracting" || u.status === "pending") return 2000;
        const anyGenerating = (u.question_sets ?? []).some(
          (qs) => qs.status === "generating",
        );
        return anyGenerating ? 8000 : false;
      },
    },
  });

  const anyGenerating = (upload?.question_sets ?? []).some(
    (qs) => qs.status === "generating",
  );

  const generationEvents = useUploadEvents(id, anyGenerating, () => {
    if (id)
      void queryClient.invalidateQueries({
        queryKey: getUploadsGetQueryKey(id),
      });
  });

  const { data: mySubjects } = useSubjectsListMine(
    { size: 100 },
    { query: { enabled: !!user } },
  );

  const updateMutation = useUploadsUpdate({
    mutation: {
      onSuccess: () => {
        toast.success("Subject updated");
        if (id)
          void queryClient.invalidateQueries({
            queryKey: getUploadsGetQueryKey(id),
          });
      },
      onError: () => toast.error("Failed to update"),
    },
  });

  const deleteMutation = useUploadsDelete({
    mutation: {
      onSuccess: () => {
        toast.success("Upload deleted");
        navigate("/uploads");
      },
      onError: () => toast.error("Failed to delete"),
    },
  });

  const generateMutation = useUploadsGenerate({
    mutation: {
      onSuccess: () => {
        toast.success("Generation queued");
        if (id)
          void queryClient.invalidateQueries({
            queryKey: getUploadsGetQueryKey(id),
          });
      },
      onError: (err: unknown) => {
        const message = extractError(err) ?? "Failed to start generation";
        toast.error(message);
      },
    },
  });

  if (!user) {
    navigate("/login");
    return null;
  }

  if (isLoading || !upload) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-1/2" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-[600px] w-full" />
          <Skeleton className="h-[600px] w-full" />
        </div>
      </div>
    );
  }

  const subject =
    mySubjects?.items.find((s) => s.id === upload.subject_id) ?? null;
  const meta = UPLOAD_STATUS_META[upload.status];
  const canGenerate = upload.status === "ready";

  function handleDelete() {
    if (!id) return;
    const ok = window.confirm(
      `Delete "${upload!.original_filename}"? This will also delete all question sets generated from it.`,
    );
    if (!ok) return;
    deleteMutation.mutate({ uploadId: id });
  }

  function handleSubjectChange(newSubjectId: string) {
    if (!id) return;
    updateMutation.mutate({
      uploadId: id,
      data: { subject_id: newSubjectId || null },
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/uploads"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Back to uploads
        </Link>
      </div>

      <PageHeader
        eyebrow="Upload"
        title={upload.original_filename}
        description={
          <span className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{formatBytes(upload.size_bytes)}</span>
            <span aria-hidden>·</span>
            <span>
              Uploaded{" "}
              {formatDistanceToNow(new Date(upload.created_at), {
                addSuffix: true,
              })}
            </span>
            <span aria-hidden>·</span>
            <Chip variant={meta.variant} size="sm" className="gap-1.5">
              <meta.Icon
                className={cn("size-3", meta.spin && "animate-spin")}
                strokeWidth={1.8}
              />
              {meta.label}
            </Chip>
          </span>
        }
        actions={
          <Button
            variant="outline"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="size-4" strokeWidth={1.5} />
            Delete
          </Button>
        }
      />

      {/* Subject + status timeline strip */}
      <div className="rounded-[14px] border border-border bg-card p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Subject
            </label>
            <select
              value={upload.subject_id ?? ""}
              onChange={(e) => handleSubjectChange(e.target.value)}
              className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
            >
              <option value="">No subject</option>
              {(mySubjects?.items ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} — {s.name}
                </option>
              ))}
            </select>
            {subject && (
              <p className="mt-1.5 text-xs text-muted-foreground">
                {subject.college} · year {subject.academic_year}
              </p>
            )}
          </div>
          <StatusTimeline status={upload.status} />
        </div>
        {upload.extraction_error && (
          <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            Extraction error: {upload.extraction_error}
          </p>
        )}
      </div>

      {/* Two-column body */}
      <div className="grid gap-6 lg:grid-cols-2">
        <FilePreviewPanel
          uploadId={upload.id}
          contentType={upload.content_type}
          filename={upload.original_filename}
        />
        <GenerationPanel
          uploadId={upload.id}
          canGenerate={canGenerate}
          uploadStatus={upload.status}
          extractedTextPreview={upload.extracted_text_preview}
          isGenerating={generateMutation.isPending}
          onGenerate={(settings) => {
            if (!id) return;
            generateMutation.mutate({
              uploadId: id,
              data: settings as GenerateRequest,
            });
          }}
        />
      </div>

      {/* Live generation progress (SSE) */}
      {anyGenerating && generationEvents.events.length > 0 && (
        <GenerationProgress state={generationEvents} />
      )}

      {/* Generations history */}
      <section className="space-y-3">
        <h2 className="text-base font-medium text-foreground">
          Generations
          {upload.question_sets && upload.question_sets.length > 0 && (
            <span className="ml-2 text-xs text-muted-foreground">
              ({upload.question_sets.length})
            </span>
          )}
        </h2>
        {!upload.question_sets || upload.question_sets.length === 0 ? (
          <div className="rounded-[14px] border border-dashed border-border bg-card/40 p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No question sets yet. Configure the panel above and click{" "}
              <strong>Generate</strong> to create your first one.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {upload.question_sets.map((qs) => {
              const qm = QS_STATUS_META[qs.status];
              const settings = qs.generation_settings as Partial<GenerationSettings>;
              return (
                <li
                  key={qs.id}
                  className="flex items-center justify-between gap-4 rounded-[14px] border border-border bg-card p-4"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {qs.title}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {qs.question_count > 0
                        ? `${qs.question_count} questions · `
                        : ""}
                      {settings.count
                        ? `requested ${settings.count} · `
                        : ""}
                      {formatDistanceToNow(new Date(qs.created_at), {
                        addSuffix: true,
                      })}
                    </p>
                    {qs.generation_error && (
                      <p className="mt-1 truncate text-xs text-destructive">
                        {qs.generation_error}
                      </p>
                    )}
                  </div>
                  <Chip variant={qm.variant} size="sm" className="gap-1.5">
                    <qm.Icon
                      className={cn(
                        "size-3",
                        qs.status === "generating" && "animate-pulse",
                      )}
                      strokeWidth={1.8}
                    />
                    {qm.label}
                  </Chip>
                  {qs.status === "draft" || qs.status === "published" ? (
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/drafts/${qs.id}`}>
                        Open
                        <ArrowRight className="size-3.5" strokeWidth={1.5} />
                      </Link>
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---------- Live generation progress (SSE) ----------

type StageKey =
  | "analyze"
  | "segment"
  | "sections"
  | "judge"
  | "dedupe"
  | "done";

const STAGE_LABELS: Record<StageKey, string> = {
  analyze: "Analyzing document",
  segment: "Segmenting sections",
  sections: "Generating questions per section",
  judge: "Judging quality",
  dedupe: "Removing duplicates",
  done: "Complete",
};

const STAGE_ORDER: StageKey[] = [
  "analyze",
  "segment",
  "sections",
  "judge",
  "dedupe",
  "done",
];

function deriveStage(events: UploadEvent[]): StageKey {
  let stage: StageKey = "analyze";
  for (const e of events) {
    if (e.type === "analyze.completed") stage = "segment";
    else if (e.type === "segment.completed") stage = "sections";
    else if (e.type === "judge.completed") stage = "judge";
    else if (e.type === "dedupe.completed") stage = "dedupe";
    else if (e.type === "generate.completed") stage = "done";
  }
  return stage;
}

function GenerationProgress({
  state,
}: {
  state: ReturnType<typeof useUploadEvents>;
}) {
  const { events, errored } = state;
  const stage = deriveStage(events);
  const currentIdx = STAGE_ORDER.indexOf(stage);

  // Per-section completion tracking.
  const sectionsTotal =
    (events.find((e) => e.type === "segment.completed") as
      | Extract<UploadEvent, { type: "segment.completed" }>
      | undefined)?.sections ?? 0;
  const sectionsDone = events.filter(
    (e) => e.type === "generate.section.completed",
  ).length;

  const errorEvent = events.find((e) => e.type === "error") as
    | Extract<UploadEvent, { type: "error" }>
    | undefined;
  const doneEvent = events.find((e) => e.type === "generate.completed") as
    | Extract<UploadEvent, { type: "generate.completed" }>
    | undefined;

  return (
    <section className="rounded-[14px] border border-border bg-card p-5">
      <div className="mb-4 flex items-center gap-2">
        {errored ? (
          <XCircle className="size-4 text-destructive" strokeWidth={1.8} />
        ) : stage === "done" ? (
          <CheckCircle2 className="size-4 text-primary" strokeWidth={1.8} />
        ) : (
          <Loader2 className="size-4 animate-spin text-primary" strokeWidth={1.8} />
        )}
        <h2 className="text-base font-medium text-foreground">
          {errored ? "Generation failed" : "Generating questions"}
        </h2>
      </div>

      {errored ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {errorEvent?.message ?? "The generation pipeline reported an error."}
        </p>
      ) : (
        <ol className="space-y-2.5">
          {STAGE_ORDER.filter((s) => s !== "done").map((s, i) => {
            const reached = currentIdx >= i;
            const active = currentIdx === i && stage !== "done";
            const complete = currentIdx > i || stage === "done";
            return (
              <li key={s} className="flex items-center gap-3 text-sm">
                <span className="flex size-5 shrink-0 items-center justify-center">
                  {complete ? (
                    <CheckCircle2
                      className="size-4 text-primary"
                      strokeWidth={1.8}
                    />
                  ) : active ? (
                    <Loader2
                      className="size-4 animate-spin text-primary"
                      strokeWidth={1.8}
                    />
                  ) : (
                    <span className="size-2 rounded-full bg-muted-foreground/30" />
                  )}
                </span>
                <span
                  className={cn(
                    reached ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {STAGE_LABELS[s]}
                  {s === "sections" && sectionsTotal > 0 && (
                    <span className="ml-2 text-xs text-muted-foreground tabular-nums">
                      {sectionsDone}/{sectionsTotal}
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      )}

      {stage === "done" && doneEvent && !errored && (
        <p className="mt-4 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-foreground">
          Inserted {doneEvent.inserted ?? doneEvent.kept ?? 0} questions
          {typeof doneEvent.dropped === "number" && doneEvent.dropped > 0
            ? ` · ${doneEvent.dropped} duplicates dropped`
            : ""}
          {typeof doneEvent.auto_rejected === "number" &&
          doneEvent.auto_rejected > 0
            ? ` · ${doneEvent.auto_rejected} below quality threshold`
            : ""}
          .
        </p>
      )}
    </section>
  );
}

// ---------- Status timeline ----------

const STATUS_ORDER = ["pending", "extracting", "ready"] as const;
type LinearStatus = (typeof STATUS_ORDER)[number];

function StatusTimeline({ status }: { status: string }) {
  const isFailed = status === "failed";
  const idx = STATUS_ORDER.indexOf(status as LinearStatus);
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Pipeline
      </p>
      <ol className="flex items-center gap-1.5 text-xs">
        {STATUS_ORDER.map((s, i) => {
          const reached = idx >= i;
          const current = idx === i;
          const failedHere = isFailed && i === STATUS_ORDER.length - 1;
          return (
            <li key={s} className="flex items-center gap-1.5">
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border text-[10px] font-medium",
                  failedHere
                    ? "border-destructive bg-destructive/10 text-destructive"
                    : reached
                      ? current
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-primary bg-primary/15 text-primary"
                      : "border-border bg-muted text-muted-foreground",
                )}
              >
                {i + 1}
              </span>
              <span
                className={cn(
                  reached || failedHere
                    ? "text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </span>
              {i < STATUS_ORDER.length - 1 && (
                <span className="mx-1 h-px w-4 bg-border" aria-hidden />
              )}
            </li>
          );
        })}
        {isFailed && (
          <li className="ml-3 text-xs text-destructive">· failed</li>
        )}
      </ol>
    </div>
  );
}

// ---------- File preview ----------

function FilePreviewPanel({
  uploadId,
  contentType,
  filename,
}: {
  uploadId: string;
  contentType: string;
  filename: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setUrl(null);
    setError(null);
    uploadsPreviewUrl(uploadId)
      .then((res) => {
        if (!cancelled) setUrl(res.url);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load preview");
      });
    return () => {
      cancelled = true;
    };
  }, [uploadId]);

  const isPdf = contentType === "application/pdf";
  const isImage = contentType.startsWith("image/");
  const previewable = isPdf || isImage;

  return (
    <div className="overflow-hidden rounded-[14px] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <FileText
            className="size-4 shrink-0 text-muted-foreground"
            strokeWidth={1.5}
          />
          <p className="truncate text-xs font-medium text-foreground">
            {filename}
          </p>
        </div>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            download={filename}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Download className="size-3" strokeWidth={1.8} />
            Download
          </a>
        )}
      </div>
      <div className="bg-muted/30">
        {error ? (
          <div className="p-12 text-center">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        ) : !url ? (
          <Skeleton className="m-6 h-[600px] w-[calc(100%-3rem)]" />
        ) : !previewable ? (
          <div className="p-12 text-center">
            <p className="text-sm text-muted-foreground">
              Preview not supported for this file type.
            </p>
            <Button asChild variant="outline" size="sm" className="mt-3">
              <a href={url} target="_blank" rel="noreferrer" download={filename}>
                <Download className="size-3.5" strokeWidth={1.5} />
                Download file
              </a>
            </Button>
          </div>
        ) : isPdf ? (
          <iframe
            src={url}
            title={`Preview of ${filename}`}
            className="h-[640px] w-full border-0 bg-white"
          />
        ) : (
          <img
            src={url}
            alt={filename}
            className="max-h-[640px] w-full object-contain"
          />
        )}
      </div>
    </div>
  );
}

// ---------- Generation panel ----------

function GenerationPanel({
  uploadId,
  canGenerate,
  uploadStatus,
  extractedTextPreview,
  isGenerating,
  onGenerate,
}: {
  uploadId: string;
  canGenerate: boolean;
  uploadStatus: string;
  extractedTextPreview?: string | null;
  isGenerating: boolean;
  onGenerate: (settings: GenerationSettings) => void;
}) {
  const { data: defaults } = useUploadsGenerationDefaults(uploadId);
  const [settings, setSettings] = useState<GenerationSettings>(() => {
    if (typeof window === "undefined") return DEFAULT_SETTINGS;
    try {
      const stored = window.localStorage.getItem(GENERATION_LS_KEY);
      if (stored) return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    } catch {
      // fall through
    }
    return DEFAULT_SETTINGS;
  });

  function persist(next: GenerationSettings) {
    setSettings(next);
    try {
      window.localStorage.setItem(GENERATION_LS_KEY, JSON.stringify(next));
    } catch {
      /* ignore quota */
    }
  }

  const mixSum =
    settings.difficulty_mix.easy +
    settings.difficulty_mix.medium +
    settings.difficulty_mix.hard;
  const mixValid = mixSum === 100;

  function setMix(key: "easy" | "medium" | "hard", value: number) {
    persist({
      ...settings,
      difficulty_mix: { ...settings.difficulty_mix, [key]: value },
    });
  }

  return (
    <div className="rounded-[14px] border border-border bg-card p-6">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles className="size-4 text-primary" strokeWidth={1.5} />
        <h2 className="text-base font-medium text-foreground">
          Generate questions
        </h2>
      </div>

      {!canGenerate && (
        <div className="mb-5 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          {uploadStatus === "extracting" || uploadStatus === "pending"
            ? "Wait for text extraction to finish before generating."
            : uploadStatus === "failed"
              ? "Extraction failed — generation is unavailable."
              : "This upload doesn't have extracted text yet."}
        </div>
      )}

      <div className="space-y-5">
        {/* What will run + admin override */}
        {defaults && (
          <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">
              Will generate with{" "}
              <span className="font-medium text-foreground">
                {defaults.extraction_model_display}
              </span>{" "}
              <span className="text-muted-foreground">
                (profile: {defaults.profile_name})
              </span>
            </p>

            {defaults.is_admin && (
              <div className="grid grid-cols-1 gap-2">
                <div>
                  <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Override model (admin)
                  </label>
                  <select
                    value={settings.extraction_model_id ?? ""}
                    onChange={(e) =>
                      persist({
                        ...settings,
                        extraction_model_id: e.target.value || null,
                      })
                    }
                    className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
                  >
                    <option value="">Profile default</option>
                    {defaults.models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.display_name} ({m.provider})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Override profile (admin)
                  </label>
                  <select
                    value={settings.profile_id ?? ""}
                    onChange={(e) =>
                      persist({
                        ...settings,
                        profile_id: e.target.value || null,
                      })
                    }
                    className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
                  >
                    <option value="">Resolve automatically</option>
                    {defaults.profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                        {p.is_default ? " (default)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Count */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Number of questions
            </label>
            <span className="text-sm font-semibold text-foreground tabular-nums">
              {settings.count}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={50}
            value={settings.count}
            onChange={(e) =>
              persist({ ...settings, count: parseInt(e.target.value, 10) })
            }
            className="w-full accent-primary"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>1</span>
            <span>50</span>
          </div>
        </div>

        {/* Difficulty mix */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Difficulty mix
            </label>
            <span
              className={cn(
                "text-xs font-medium tabular-nums",
                mixValid
                  ? "text-muted-foreground"
                  : "text-destructive",
              )}
            >
              {mixSum}/100
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(["easy", "medium", "hard"] as const).map((k) => (
              <div key={k}>
                <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  {k}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={settings.difficulty_mix[k]}
                    onChange={(e) =>
                      setMix(k, Math.max(0, Math.min(100, +e.target.value || 0)))
                    }
                    className="h-10 w-full rounded-lg border border-border bg-background pl-3 pr-7 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                    %
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Question types — only MCQ is wired up server-side today */}
        <div>
          <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Question types
          </label>
          <div className="flex flex-wrap gap-2">
            <Chip variant="primary" className="gap-1.5">
              MCQ
            </Chip>
            <Chip variant="outline" className="opacity-50">
              True / False · soon
            </Chip>
            <Chip variant="outline" className="opacity-50">
              Short answer · soon
            </Chip>
          </div>
        </div>

        {/* Language */}
        <div>
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Language
          </label>
          <select
            value={settings.language}
            onChange={(e) => persist({ ...settings, language: e.target.value })}
            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
          >
            <option value="en">English</option>
            <option value="ar">العربية (Arabic)</option>
          </select>
        </div>

        {/* Extracted text preview (collapsible feel via line-clamp) */}
        {extractedTextPreview && (
          <details className="rounded-md border border-border bg-muted/30">
            <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
              Source text preview
            </summary>
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap break-words px-3 pb-3 text-[11px] leading-relaxed text-muted-foreground">
              {extractedTextPreview}
            </pre>
          </details>
        )}

        {/* CTA */}
        <Button
          onClick={() => onGenerate(settings)}
          disabled={!canGenerate || isGenerating || !mixValid}
          className="w-full"
          size="lg"
        >
          <Sparkles className="size-4" strokeWidth={1.5} />
          {isGenerating ? "Queuing…" : "Generate questions"}
        </Button>
        {!mixValid && (
          <p className="text-center text-xs text-destructive">
            Difficulty mix must sum to 100%.
          </p>
        )}
      </div>
    </div>
  );
}

// ---------- helpers ----------

function extractError(err: unknown): string | null {
  if (typeof err !== "object" || err === null) return null;
  const e = err as { response?: { data?: { detail?: unknown } } };
  const detail = e.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return null;
}
