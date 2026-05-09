import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { FileText, Upload as UploadIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useUploadsList } from "@/api/generated/endpoints/uploads/uploads";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import { UploadStatus } from "@/api/generated/schemas";
import type { UploadResponse } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { EmptyState } from "@/components/design/EmptyState";
import { Chip } from "@/components/design/Chip";
import { cn } from "@/lib/utils";
import { UPLOAD_STATUS_META, formatBytes } from "./status-meta";

const STATUS_FILTERS: { value: UploadStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "extracting", label: "Processing" },
  { value: "ready", label: "Ready" },
  { value: "failed", label: "Failed" },
];

const PAGE_SIZE = 20;

export default function UploadsListPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [statusFilter, setStatusFilter] = useState<UploadStatus | "all">("all");
  const [subjectId, setSubjectId] = useState<string>("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data: mySubjects } = useSubjectsListMine(
    { size: 100 },
    { query: { enabled: !!user } },
  );

  const { data, isLoading, isError, refetch } = useUploadsList(
    {
      status: statusFilter === "all" ? undefined : statusFilter,
      subject_id: subjectId || undefined,
      page,
      size: PAGE_SIZE,
    },
    {
      query: {
        enabled: !!user,
        // Poll while anything in the page is mid-flight.
        refetchInterval: (query) => {
          const items = (query.state.data?.items ?? []) as UploadResponse[];
          return items.some(
            (u) => u.status === "extracting" || u.status === "pending",
          )
            ? 2500
            : false;
        },
      },
    },
  );

  if (!user) {
    navigate("/login");
    return null;
  }

  const items = (data?.items ?? []).filter((u) =>
    search.trim()
      ? u.original_filename.toLowerCase().includes(search.trim().toLowerCase())
      : true,
  );
  const subjectMap = new Map(
    (mySubjects?.items ?? []).map((s) => [s.id, s] as const),
  );

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Library"
        title="My uploads"
        description="Every file you've uploaded. Drop into a file to configure question generation."
        actions={
          <Button asChild>
            <Link to="/upload">
              <UploadIcon className="size-4" strokeWidth={1.5} />
              Upload material
            </Link>
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex flex-col gap-4 rounded-[14px] border border-border bg-card p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Search filename
          </label>
          <input
            type="text"
            value={search}
            placeholder="lecture-notes.pdf"
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
          />
        </div>
        <div className="sm:w-56">
          <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Subject
          </label>
          <select
            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
            value={subjectId}
            onChange={(e) => {
              setSubjectId(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Any subject</option>
            {(mySubjects?.items ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} — {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Status chips */}
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              setStatusFilter(opt.value);
              setPage(1);
            }}
            className={cn(
              "rounded-full border px-4 py-1.5 text-xs font-medium transition-colors",
              statusFilter === opt.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Body */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-[14px]" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          title="Couldn't load your uploads"
          description="Please try again."
          action={
            <Button variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={search.trim() ? "No matches" : "Nothing here yet"}
          description={
            search.trim()
              ? "No uploads match your search."
              : "Upload a PDF, DOCX, or scan to start generating questions."
          }
          action={
            !search.trim() ? (
              <Button asChild>
                <Link to="/upload">
                  <UploadIcon className="size-4" strokeWidth={1.5} />
                  Upload material
                </Link>
              </Button>
            ) : null
          }
        />
      ) : (
        <div className="space-y-2">
          {items.map((u) => (
            <UploadRow
              key={u.id}
              upload={u}
              subjectName={
                u.subject_id ? subjectMap.get(u.subject_id)?.name : undefined
              }
            />
          ))}

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <p className="text-xs text-muted-foreground">
                Page {page} of {totalPages} · {total} total
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function UploadRow({
  upload,
  subjectName,
}: {
  upload: UploadResponse;
  subjectName?: string;
}) {
  const meta = UPLOAD_STATUS_META[upload.status];
  return (
    <Link
      to={`/uploads/${upload.id}`}
      className="block rounded-[14px] border border-border bg-card p-5 transition-colors hover:border-foreground/20 hover:bg-muted/40"
    >
      <div className="flex items-start gap-4">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted">
          <FileText
            className="size-5 text-muted-foreground"
            strokeWidth={1.5}
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {upload.original_filename}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatBytes(upload.size_bytes)}
            {subjectName ? <> · {subjectName}</> : null} ·{" "}
            {formatDistanceToNow(new Date(upload.created_at), {
              addSuffix: true,
            })}
          </p>
        </div>
        <Chip variant={meta.variant} className="gap-1.5">
          <meta.Icon
            className={cn("size-3", meta.spin && "animate-spin")}
            strokeWidth={1.8}
          />
          {meta.label}
        </Chip>
      </div>
    </Link>
  );
}
