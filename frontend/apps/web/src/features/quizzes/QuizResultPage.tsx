import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  RotateCcw,
  Trophy,
  XCircle,
} from "lucide-react";
import { useQuizzesGetResult } from "@/api/generated/endpoints/quizzes/quizzes";
import type { QuizQuestionResult } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { cn } from "@/lib/utils";

export default function QuizResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const { data, isLoading, error } = useQuizzesGetResult(id ?? "", {
    query: { enabled: !!user && !!id },
  });

  if (!user) {
    navigate("/login");
    return null;
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-72 w-full rounded-[14px]" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="text-center text-sm text-destructive">
        Failed to load result.
        <div className="mt-4">
          <Button variant="outline" onClick={() => navigate("/history")}>
            Back to history
          </Button>
        </div>
      </div>
    );
  }

  const accuracyPct = Math.round((data.accuracy ?? 0) * 100);
  const trendPct =
    data.trend === null || data.trend === undefined
      ? null
      : Math.round(data.trend * 100);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <button
        onClick={() => navigate("/history")}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="size-3.5" />
        History
      </button>

      <PageHeader
        eyebrow="Quiz result"
        title="Your performance"
        description={
          data.completed_at
            ? `Completed ${new Date(data.completed_at).toLocaleString()}`
            : "Session is in progress"
        }
      />

      {/* Score hero */}
      <div className="flex flex-col items-stretch gap-6 rounded-[14px] border border-border bg-card p-8 sm:flex-row sm:items-center sm:gap-10">
        <ScoreDonut
          correct={data.correct_count}
          incorrect={data.incorrect_count}
          skipped={data.skipped_count}
        />

        <div className="flex-1 space-y-3">
          <div className="flex items-baseline gap-3">
            <CountUp
              value={accuracyPct}
              className="text-6xl font-semibold tracking-tight text-foreground"
            />
            <span className="text-2xl font-medium text-muted-foreground">%</span>
            {trendPct !== null && (
              <span
                className={cn(
                  "ml-1 inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium",
                  trendPct > 0
                    ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
                    : trendPct < 0
                      ? "bg-destructive/10 text-destructive"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {trendPct > 0 ? (
                  <ArrowUpRight className="size-3" strokeWidth={2} />
                ) : trendPct < 0 ? (
                  <ArrowDownRight className="size-3" strokeWidth={2} />
                ) : null}
                {trendPct > 0 ? "+" : ""}
                {trendPct}% vs last
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">
              {data.correct_count} correct
            </span>{" "}
            · {data.incorrect_count} incorrect
            {data.skipped_count > 0 && ` · ${data.skipped_count} skipped`} · out of{" "}
            {data.total} total
          </p>

          {/* Difficulty breakdown */}
          {data.breakdown_by_difficulty.length > 0 && (
            <div className="grid grid-cols-3 gap-3 pt-2">
              {data.breakdown_by_difficulty.map((b) => {
                const pct = b.total ? Math.round((b.correct / b.total) * 100) : 0;
                return (
                  <div
                    key={b.difficulty}
                    className="rounded-lg border border-border bg-muted/30 p-3"
                  >
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {b.difficulty}
                    </p>
                    <p className="mt-1 text-base font-semibold text-foreground">
                      {b.correct}
                      <span className="text-muted-foreground">/{b.total}</span>{" "}
                      <span className="text-xs font-normal text-muted-foreground">
                        ({pct}%)
                      </span>
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* CTAs */}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => navigate("/quiz")}>
          <RotateCcw className="size-3.5" strokeWidth={1.5} />
          New quiz
        </Button>
        <Button variant="outline" onClick={() => navigate("/history")}>
          See all attempts
        </Button>
      </div>

      {/* Per-question breakdown */}
      <div className="space-y-3">
        <h2 className="text-base font-medium text-foreground">Question breakdown</h2>
        <div className="space-y-2">
          {data.questions.map((q, i) => (
            <QuestionRow key={q.question_id} q={q} index={i + 1} />
          ))}
        </div>
      </div>

      {data.questions.length === 0 && (
        <div className="rounded-[14px] border border-border bg-card p-8 text-center">
          <Trophy className="mx-auto size-10 text-muted-foreground/40" />
          <p className="mt-3 text-sm text-muted-foreground">
            No questions to break down for this session.
          </p>
        </div>
      )}
    </div>
  );
}

function ScoreDonut({
  correct,
  incorrect,
  skipped,
}: {
  correct: number;
  incorrect: number;
  skipped: number;
}) {
  const total = correct + incorrect + skipped;
  const c = 2 * Math.PI * 38; // circumference
  const correctLen = total ? (correct / total) * c : 0;
  const incorrectLen = total ? (incorrect / total) * c : 0;
  const skippedLen = total ? (skipped / total) * c : 0;

  return (
    <div className="relative size-32 shrink-0">
      <svg viewBox="0 0 100 100" className="-rotate-90">
        <circle cx="50" cy="50" r="38" fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r="38"
          fill="none"
          stroke="var(--success)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${correctLen} ${c}`}
        />
        <circle
          cx="50"
          cy="50"
          r="38"
          fill="none"
          stroke="var(--destructive)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${incorrectLen} ${c}`}
          strokeDashoffset={-correctLen}
        />
        <circle
          cx="50"
          cy="50"
          r="38"
          fill="none"
          stroke="var(--muted-foreground)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${skippedLen} ${c}`}
          strokeDashoffset={-(correctLen + incorrectLen)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-2xl font-semibold tracking-tight text-foreground">
          {correct}
        </p>
        <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          correct
        </p>
      </div>
    </div>
  );
}

function CountUp({ value, className }: { value: number; className?: string }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const duration = 800;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setDisplay(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <span className={className}>{display}</span>;
}

function QuestionRow({ q, index }: { q: QuizQuestionResult; index: number }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const correct = q.is_correct;
  const skipped = q.selected_choice_id === null;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/30"
      >
        <span
          className={cn(
            "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            correct
              ? "bg-[color:var(--success)]/15 text-[color:var(--success)]"
              : skipped
                ? "bg-muted text-muted-foreground"
                : "bg-destructive/15 text-destructive",
          )}
        >
          {correct ? (
            <CheckCircle2 className="size-3.5" strokeWidth={2} />
          ) : skipped ? (
            <span>·</span>
          ) : (
            <XCircle className="size-3.5" strokeWidth={2} />
          )}
        </span>
        <span className="text-xs font-medium text-muted-foreground">{index}.</span>
        <span className="line-clamp-1 flex-1 text-sm text-foreground">{q.text}</span>
        <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {q.difficulty}
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
          strokeWidth={1.5}
        />
      </button>
      {open && (
        <div ref={ref} className="space-y-3 border-t border-border bg-background px-6 py-5">
          <p className="font-study text-base leading-relaxed text-foreground">
            {q.text}
          </p>
          <ul className="space-y-1.5">
            {q.choices.map((c) => {
              const isCorrect = c.id === q.correct_choice_id;
              const isPick = c.id === q.selected_choice_id;
              return (
                <li
                  key={c.id}
                  className={cn(
                    "flex items-start gap-3 rounded-md border px-3 py-2 text-sm",
                    isCorrect
                      ? "border-[color:var(--success)]/40 bg-[color:var(--success)]/5"
                      : isPick && !isCorrect
                        ? "border-destructive/40 bg-destructive/5"
                        : "border-transparent",
                  )}
                >
                  {isCorrect ? (
                    <CheckCircle2
                      className="mt-0.5 size-4 shrink-0 text-[color:var(--success)]"
                      strokeWidth={1.5}
                    />
                  ) : isPick ? (
                    <XCircle
                      className="mt-0.5 size-4 shrink-0 text-destructive"
                      strokeWidth={1.5}
                    />
                  ) : (
                    <span className="mt-1 size-4 shrink-0 rounded-full border border-border" />
                  )}
                  <span className="font-study text-foreground">{c.text}</span>
                  {isPick && (
                    <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Your pick
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
          {q.explanation && (
            <div className="rounded-md border-l-2 border-primary/40 bg-muted/30 px-3 py-2">
              <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                Explanation
              </p>
              <p className="mt-1 font-study text-sm text-muted-foreground">
                {q.explanation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
