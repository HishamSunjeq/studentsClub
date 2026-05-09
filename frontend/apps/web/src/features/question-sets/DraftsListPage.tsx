import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, FileText, Sparkles } from "lucide-react";
import { useQuestionSetsListMine } from "@/api/generated/endpoints/question-sets/question-sets";
import type { QuestionSetStatus } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { EmptyState } from "@/components/design";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: { value: QuestionSetStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Drafts" },
  { value: "published", label: "Published" },
  { value: "rejected", label: "Rejected" },
];

const STATUS_STYLES: Record<QuestionSetStatus, string> = {
  generating: "bg-primary/10 text-primary border-primary/20",
  generation_failed: "bg-destructive/10 text-destructive border-destructive/20",
  draft: "bg-[color:var(--warning)]/10 text-[color:var(--warning)] border-[color:var(--warning)]/20",
  published:
    "bg-[color:var(--success)]/10 text-[color:var(--success)] border-[color:var(--success)]/20",
  rejected: "bg-destructive/10 text-destructive border-destructive/20",
};

export default function DraftsListPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [filter, setFilter] = useState<QuestionSetStatus | "all">("all");

  const { data, isLoading } = useQuestionSetsListMine(
    {
      size: 50,
      status: filter === "all" ? undefined : filter,
    },
    { query: { enabled: !!user } },
  );

  if (!user) {
    navigate("/login");
    return null;
  }

  const items = data?.items ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Question Sets"
        title="My drafts"
        description="Review AI-generated questions before publishing them to your subject's question bank."
      >
        <Button onClick={() => navigate("/upload")}>
          <Sparkles className="size-3.5" strokeWidth={1.5} />
          New upload
        </Button>
      </PageHeader>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "rounded-full px-4 py-1.5 text-xs font-medium transition-colors",
              filter === f.value
                ? "bg-primary text-primary-foreground"
                : "border border-border bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-[14px]" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No question sets yet"
          description="Upload study material to generate your first AI-drafted question set."
          action={
            <Button onClick={() => navigate("/upload")}>
              <Sparkles className="size-3.5" strokeWidth={1.5} />
              Upload material
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {items.map((qs) => (
            <button
              key={qs.id}
              onClick={() => navigate(`/drafts/${qs.id}`)}
              className="group flex w-full items-start justify-between gap-4 rounded-[14px] border border-border bg-card p-5 text-left transition-colors hover:border-ring/40"
            >
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <FileText
                    className="size-4 text-muted-foreground"
                    strokeWidth={1.5}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                    {qs.title}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {qs.ai_model} · {qs.tokens_used.toLocaleString()} tokens ·{" "}
                    {new Date(qs.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <span
                  className={cn(
                    "rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                    STATUS_STYLES[qs.status],
                  )}
                >
                  {qs.status}
                </span>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
