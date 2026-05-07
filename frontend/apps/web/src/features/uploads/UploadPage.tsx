import { useMutation, useQueries } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import {
  CheckCircle2,
  CloudUpload,
  FileText,
  Loader2,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import {
  uploadsCreate,
  uploadsFinalize,
  uploadsGet,
} from "@/api/generated/endpoints/uploads/uploads";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import type { UploadResponse } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { ALLOWED_TYPES, MAX_BYTES, uploadToS3 } from "@/features/uploads/uploads.utils";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/design/PageHeader";
import { cn } from "@/lib/utils";

type QueueItemStatus =
  | "pending"
  | "uploading"
  | "finalizing"
  | "processing"
  | "ready"
  | "error";

type QueueItem = {
  localId: string;
  file: File;
  subjectId: string;
  status: QueueItemStatus;
  progress: number;
  uploadId?: string;
  questionSetId?: string;
  errorMsg?: string;
};

export default function UploadPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [defaultSubjectId, setDefaultSubjectId] = useState("");
  const [dragging, setDragging] = useState(false);
  const [pickError, setPickError] = useState("");

  const { data: mySubjects } = useSubjectsListMine(
    { size: 100 },
    { query: { enabled: !!user } },
  );

  // Poll uploads that are still being processed (have uploadId, not yet ready/error).
  const pollableItems = queue.filter(
    (q) => q.uploadId && (q.status === "processing" || q.status === "finalizing"),
  );
  const pollResults = useQueries({
    queries: pollableItems.map((q) => ({
      queryKey: ["uploads", q.uploadId, "poll"],
      queryFn: () => uploadsGet(q.uploadId!),
      refetchInterval: 1500,
      enabled: !!q.uploadId,
    })),
  });

  // Reflect server-side status into the queue
  pollResults.forEach((res, i) => {
    const data = res.data as UploadResponse | undefined;
    if (!data) return;
    const item = pollableItems[i];
    if (!item) return;
    if (data.status === "finalized" && item.status !== "ready") {
      setQueue((q) =>
        q.map((it) =>
          it.localId === item.localId ? { ...it, status: "ready", progress: 100 } : it,
        ),
      );
    } else if (data.status === "failed" && item.status !== "error") {
      setQueue((q) =>
        q.map((it) =>
          it.localId === item.localId
            ? { ...it, status: "error", errorMsg: "AI extraction failed" }
            : it,
        ),
      );
    }
  });

  function pickFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    setPickError("");
    const accepted: QueueItem[] = [];
    for (const f of arr) {
      if (!ALLOWED_TYPES[f.type]) {
        setPickError(`${f.name}: file type not allowed`);
        continue;
      }
      if (f.size > MAX_BYTES) {
        setPickError(`${f.name}: exceeds 50 MB limit`);
        continue;
      }
      accepted.push({
        localId: crypto.randomUUID(),
        file: f,
        subjectId: defaultSubjectId,
        status: "pending",
        progress: 0,
      });
    }
    if (accepted.length) setQueue((q) => [...q, ...accepted]);
  }

  function updateItem(localId: string, patch: Partial<QueueItem>) {
    setQueue((q) => q.map((it) => (it.localId === localId ? { ...it, ...patch } : it)));
  }

  function removeItem(localId: string) {
    setQueue((q) => q.filter((it) => it.localId !== localId));
  }

  const startMutation = useMutation({
    mutationFn: async (item: QueueItem) => {
      updateItem(item.localId, { status: "uploading", progress: 5 });

      const presign = await uploadsCreate({
        filename: item.file.name,
        content_type: item.file.type,
        size_bytes: item.file.size,
        subject_id: item.subjectId || undefined,
      });

      updateItem(item.localId, { uploadId: presign.upload_id, progress: 30 });

      await uploadToS3(presign.presigned_url, item.file);
      updateItem(item.localId, { progress: 70, status: "finalizing" });

      await uploadsFinalize(presign.upload_id);
      updateItem(item.localId, { progress: 90, status: "processing" });
      // From here, the polling effect picks up the ready/failed transition.
    },
    onError: (err: Error, item: QueueItem) => {
      updateItem(item.localId, {
        status: "error",
        errorMsg: err.message || "Upload failed",
      });
    },
  });

  function startAll() {
    queue
      .filter((q) => q.status === "pending")
      .forEach((item) => startMutation.mutate(item));
  }

  if (!user) {
    navigate("/login");
    return null;
  }

  const pendingCount = queue.filter((q) => q.status === "pending").length;

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="New Material"
        title="Upload study material"
        description="Drop your notes, slides, or scanned exams. AI generates draft questions for your review."
      />

      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files?.length) pickFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-[14px] border-2 border-dashed p-16 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/40 hover:bg-muted/30",
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          accept={Object.keys(ALLOWED_TYPES).join(",")}
          onChange={(e) => e.target.files && pickFiles(e.target.files)}
        />
        <div className="flex size-12 items-center justify-center rounded-full bg-primary/10">
          <CloudUpload className="size-6 text-primary" strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-base font-medium text-foreground">
            Drop files here or <span className="text-primary underline">browse</span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            PDF, DOCX, PNG, JPEG, WEBP · up to 50 MB each
          </p>
        </div>
      </div>

      {pickError && <p className="text-sm text-destructive">{pickError}</p>}

      {/* Default subject for the batch */}
      {mySubjects && mySubjects.items.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Default subject for new files
          </label>
          <select
            className="h-10 max-w-md rounded-lg border border-border bg-card px-3 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
            value={defaultSubjectId}
            onChange={(e) => setDefaultSubjectId(e.target.value)}
          >
            <option value="">No subject</option>
            {mySubjects.items.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Queue */}
      {queue.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium text-foreground">
              Queue ({queue.length})
            </h2>
            {pendingCount > 0 && (
              <Button onClick={startAll} disabled={startMutation.isPending}>
                Start {pendingCount} upload{pendingCount === 1 ? "" : "s"}
              </Button>
            )}
          </div>

          <div className="space-y-2">
            {queue.map((item) => (
              <UploadRow
                key={item.localId}
                item={item}
                subjects={mySubjects?.items ?? []}
                onSubjectChange={(sid) =>
                  updateItem(item.localId, { subjectId: sid })
                }
                onRemove={() => removeItem(item.localId)}
                onReviewClick={() =>
                  // Drafts list is the simplest target since queryset id isn't on UploadResponse
                  navigate(`/drafts`)
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const STATUS_META: Record<
  QueueItemStatus,
  { label: string; tone: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  pending: { label: "Ready to upload", tone: "text-muted-foreground", Icon: FileText },
  uploading: { label: "Uploading…", tone: "text-primary", Icon: Loader2 },
  finalizing: { label: "Finalizing…", tone: "text-primary", Icon: Loader2 },
  processing: { label: "AI generating…", tone: "text-primary", Icon: Sparkles },
  ready: { label: "Draft ready", tone: "text-[color:var(--success)]", Icon: CheckCircle2 },
  error: { label: "Failed", tone: "text-destructive", Icon: XCircle },
};

function UploadRow({
  item,
  subjects,
  onSubjectChange,
  onRemove,
  onReviewClick,
}: {
  item: QueueItem;
  subjects: { id: string; name: string; code: string }[];
  onSubjectChange: (id: string) => void;
  onRemove: () => void;
  onReviewClick: () => void;
}) {
  const meta = STATUS_META[item.status];
  const isInProgress =
    item.status === "uploading" ||
    item.status === "finalizing" ||
    item.status === "processing";

  return (
    <div className="rounded-[14px] border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
            <FileText className="size-4 text-muted-foreground" strokeWidth={1.5} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">
              {item.file.name}
            </p>
            <p className="text-xs text-muted-foreground">
              {(item.file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={cn(
              "flex items-center gap-1.5 text-xs font-medium",
              meta.tone,
            )}
          >
            <meta.Icon
              className={cn(
                "size-3.5",
                (item.status === "uploading" ||
                  item.status === "finalizing" ||
                  item.status === "processing") &&
                  "animate-spin",
              )}
            />
            {meta.label}
          </span>
          {item.status === "pending" && (
            <button
              onClick={onRemove}
              className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Remove from queue"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
      </div>

      {/* Per-file subject (only editable while pending) */}
      {item.status === "pending" && subjects.length > 0 && (
        <div className="mt-4">
          <select
            className="h-8 w-full rounded-md border border-border bg-muted/40 px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            value={item.subjectId}
            onChange={(e) => onSubjectChange(e.target.value)}
          >
            <option value="">No subject</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Progress bar */}
      {isInProgress && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${item.progress}%` }}
          />
        </div>
      )}

      {item.errorMsg && (
        <p className="mt-3 text-xs text-destructive">{item.errorMsg}</p>
      )}

      {item.status === "ready" && (
        <div className="mt-4 flex justify-end">
          <Button size="sm" variant="outline" onClick={onReviewClick}>
            Review draft →
          </Button>
        </div>
      )}
    </div>
  );
}
