import { useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, BrainCircuit, History as HistoryIcon } from "lucide-react";
import { useQuizzesListMine } from "@/api/generated/endpoints/quizzes/quizzes";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import type { QuizSessionStatus } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { EmptyState } from "@/components/design";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: { value: QuizSessionStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "in_progress", label: "In progress" },
  { value: "abandoned", label: "Abandoned" },
];

const STATUS_STYLES: Record<QuizSessionStatus, string> = {
  completed:
    "bg-[color:var(--success)]/10 text-[color:var(--success)] border-[color:var(--success)]/20",
  in_progress: "bg-primary/10 text-primary border-primary/20",
  abandoned: "bg-muted text-muted-foreground border-border",
};

export default function QuizHistoryPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [statusFilter, setStatusFilter] = useState<QuizSessionStatus | "all">("all");
  const [subjectId, setSubjectId] = useState("");
  const [page, setPage] = useState(1);

  const { data: mySubjects } = useSubjectsListMine(
    { size: 100 },
    { query: { enabled: !!user } },
  );

  const { data, isLoading } = useQuizzesListMine(
    {
      page,
      size: 20,
      status: statusFilter === "all" ? undefined : statusFilter,
      subject_id: subjectId || undefined,
    },
    { query: { enabled: !!user } },
  );

  if (!user) {
    navigate("/login");
    return null;
  }

  const items = data?.items ?? [];
  const subjectsById = new Map(mySubjects?.items.map((s) => [s.id, s]) ?? []);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Activity"
        title="Quiz history"
        description="Every practice session you've taken, with scores and timestamps."
      >
        <Button onClick={() => navigate("/quiz")}>
          <BrainCircuit className="size-3.5" strokeWidth={1.5} />
          Start a quiz
        </Button>
      </PageHeader>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => {
                setStatusFilter(f.value);
                setPage(1);
              }}
              className={cn(
                "rounded-full px-4 py-1.5 text-xs font-medium transition-colors",
                statusFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "border border-border bg-muted text-muted-foreground hover:bg-muted/80",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {(mySubjects?.items.length ?? 0) > 0 && (
          <select
            value={subjectId}
            onChange={(e) => {
              setSubjectId(e.target.value);
              setPage(1);
            }}
            className="ml-auto h-8 rounded-full border border-border bg-muted px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">All subjects</option>
            {mySubjects?.items.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No quiz attempts yet"
          description="Start a quiz to begin tracking your progress here."
          action={
            <Button onClick={() => navigate("/quiz")}>
              <BrainCircuit className="size-3.5" strokeWidth={1.5} />
              Start a quiz
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {items.map((s) => {
            const pct =
              s.total_questions > 0
                ? Math.round((s.score / s.total_questions) * 100)
                : 0;
            const subject = subjectsById.get(s.subject_id);
            const target =
              s.status === "completed"
                ? `/quiz/${s.id}/result`
                : s.status === "in_progress"
                  ? `/quiz/${s.id}`
                  : `/quiz/${s.id}/result`;
            return (
              <button
                key={s.id}
                onClick={() => navigate(target)}
                className="group flex w-full items-center gap-4 rounded-[14px] border border-border bg-card p-4 text-left transition-colors hover:border-ring/40"
              >
                <div className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <span className="text-base font-semibold text-foreground">
                    {pct}%
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {subject?.name ?? "Unknown subject"}
                    {subject?.code && (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {subject.code}
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {s.score} / {s.total_questions} ·{" "}
                    {new Date(s.created_at).toLocaleString()}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                    STATUS_STYLES[s.status],
                  )}
                >
                  {s.status === "in_progress" ? "in progress" : s.status}
                </span>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground" />
              </button>
            );
          })}

          {(data?.pages ?? 1) > 1 && (
            <div className="flex items-center justify-center gap-2 pt-3">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                {page} / {data?.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page === data?.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
