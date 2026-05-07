import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { toast } from "sonner";
import {
  CheckCircle2,
  ChevronLeft,
  Flag,
  LayoutGrid,
  Loader2,
  X,
  XCircle,
} from "lucide-react";
import {
  quizzesComplete,
  quizzesSubmitAnswer,
  useQuizzesGetWithQuestions,
} from "@/api/generated/endpoints/quizzes/quizzes";
import type {
  QuizAnswerResponse,
  QuizSessionWithQuestionsResponse,
} from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const TIME_PER_QUESTION = 60; // seconds for timed mode

interface LocationState {
  session?: QuizSessionWithQuestionsResponse;
}

export default function QuizPlayerPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const stateSession = (location.state as LocationState | null)?.session;

  // Skip the fetch when state is already populated (came directly from QuizStartPage).
  const { data: fetched, isLoading, error } = useQuizzesGetWithQuestions(
    id ?? "",
    {
      query: { enabled: !!user && !!id && !stateSession },
    },
  );

  if (!user) {
    navigate("/login");
    return null;
  }
  if (!id) {
    navigate("/quiz");
    return null;
  }

  const session = stateSession ?? fetched;
  const timed = searchParams.get("timed") === "true";

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-72 w-full rounded-[14px]" />
      </div>
    );
  }
  if (error || !session) {
    return (
      <div className="text-center text-sm text-destructive">Failed to load quiz.</div>
    );
  }

  return <QuizRunner session={session} timed={timed} />;
}

function QuizRunner({
  session,
  timed,
}: {
  session: QuizSessionWithQuestionsResponse;
  timed: boolean;
}) {
  const navigate = useNavigate();
  const total = session.questions.length;

  const initialAnswered = useMemo(
    () => new Set(session.answered_question_ids ?? []),
    [session.answered_question_ids],
  );

  const initialIdx = useMemo(() => {
    const i = session.questions.findIndex((q) => !initialAnswered.has(q.id));
    return i === -1 ? Math.max(total - 1, 0) : i;
  }, [session.questions, initialAnswered, total]);

  const [answeredIds, setAnsweredIds] = useState<Set<string>>(initialAnswered);
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [currentIdx, setCurrentIdx] = useState(initialIdx);
  const [pickedChoiceId, setPickedChoiceId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<QuizAnswerResponse | null>(null);
  const [score, setScore] = useState(session.score);
  const [submitting, setSubmitting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(timed ? TIME_PER_QUESTION : 0);

  const current = session.questions[currentIdx];
  const isLast = currentIdx === total - 1;
  const allAnswered = answeredIds.size >= total && total > 0;

  // Auto-complete if user lands on a fully-answered session
  useEffect(() => {
    if (allAnswered && session.status === "in_progress" && !completing) {
      void completeAndGo();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset per-question UI when navigating
  useEffect(() => {
    setPickedChoiceId(null);
    setFeedback(null);
    if (timed) setSecondsLeft(TIME_PER_QUESTION);
  }, [currentIdx, timed]);

  // Timer
  useEffect(() => {
    if (!timed) return;
    if (feedback || submitting) return;
    if (secondsLeft <= 0) return;
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [timed, feedback, submitting, secondsLeft]);

  // Time-up → auto-pick first choice as a "skip" — actually just disable picking and require Next
  // (Backend doesn't support skip; for now, we just lock and let user move on without answering.)

  // Keyboard 1–4 to pick, Enter to next
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!current) return;
      if (e.key >= "1" && e.key <= "4") {
        const idx = Number(e.key) - 1;
        const choice = current.choices[idx];
        if (choice && !feedback && !submitting) {
          void onPick(choice.id);
        }
      } else if (e.key === "Enter" && (feedback || answeredIds.has(current.id))) {
        void onNext();
      } else if (e.key === "f" || e.key === "F") {
        toggleFlag(current.id);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, feedback, submitting, answeredIds]);

  function toggleFlag(qId: string) {
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(qId)) next.delete(qId);
      else next.add(qId);
      return next;
    });
  }

  async function onPick(choiceId: string) {
    if (feedback || submitting || !current) return;
    setPickedChoiceId(choiceId);
    setSubmitting(true);
    try {
      const res = await quizzesSubmitAnswer(session.id, {
        question_id: current.id,
        choice_id: choiceId,
      });
      setFeedback(res);
      setScore(res.score);
      setAnsweredIds((prev) => new Set(prev).add(current.id));
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail;
      toast.error(detail ?? "Failed to submit answer");
      setPickedChoiceId(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function completeAndGo() {
    setCompleting(true);
    try {
      await quizzesComplete(session.id);
      navigate(`/quiz/${session.id}/result`);
    } catch {
      toast.error("Failed to complete quiz");
    } finally {
      setCompleting(false);
    }
  }

  async function onNext() {
    if (isLast) {
      await completeAndGo();
      return;
    }
    setCurrentIdx((i) => i + 1);
  }

  if (!current) {
    return <div className="p-8 text-sm text-muted-foreground">Wrapping up…</div>;
  }

  const isAlreadyAnswered = answeredIds.has(current.id) && !feedback;
  const progress = (answeredIds.size / total) * 100;

  return (
    <div className="-mx-6 -my-8 flex h-[calc(100vh-3.5rem)] flex-col bg-background">
      {/* Slim top bar */}
      <header className="flex shrink-0 items-center justify-between border-b border-border px-6 py-3">
        <button
          onClick={() => navigate("/quiz")}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-3.5" />
          Exit
        </button>

        {/* Progress bar */}
        <div className="mx-6 flex flex-1 items-center gap-3">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {currentIdx + 1} / {total}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {timed && (
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tabular-nums",
                secondsLeft <= 10
                  ? "border-destructive/40 bg-destructive/10 text-destructive"
                  : "border-border bg-muted text-muted-foreground",
              )}
            >
              {secondsLeft}s
            </div>
          )}
          <button
            onClick={() => setMapOpen((v) => !v)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Question map"
          >
            <LayoutGrid className="size-4" strokeWidth={1.5} />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Main */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-2xl space-y-8 px-6 py-12">
            {/* Question header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-primary/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-primary">
                  Question {currentIdx + 1}
                </span>
                <span className="rounded-md bg-muted px-2 py-1 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  {current.difficulty}
                </span>
              </div>
              <button
                onClick={() => toggleFlag(current.id)}
                className={cn(
                  "rounded-md p-1.5 transition-colors",
                  flagged.has(current.id)
                    ? "text-[color:var(--warning)]"
                    : "text-muted-foreground hover:text-foreground",
                )}
                aria-label="Flag for review"
                title="Flag for review (F)"
              >
                <Flag
                  className="size-4"
                  strokeWidth={1.5}
                  fill={flagged.has(current.id) ? "currentColor" : "none"}
                />
              </button>
            </div>

            {/* Question stem (serif) */}
            <h1 className="font-study text-2xl leading-relaxed text-foreground">
              {current.text}
            </h1>

            {/* Choices */}
            <div className="space-y-3">
              {isAlreadyAnswered && (
                <p className="text-xs text-muted-foreground">
                  You've answered this. Use the question map to revisit others.
                </p>
              )}
              {current.choices.map((c, i) => {
                const isPicked = pickedChoiceId === c.id;
                const isCorrect = feedback && c.id === feedback.correct_choice_id;
                const isWrong = feedback && isPicked && !feedback.is_correct;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => onPick(c.id)}
                    disabled={!!feedback || submitting || isAlreadyAnswered}
                    className={cn(
                      "group flex w-full items-start gap-4 rounded-lg border p-4 text-left transition-colors",
                      feedback
                        ? isCorrect
                          ? "border-[color:var(--success)]/40 bg-[color:var(--success)]/10"
                          : isWrong
                            ? "border-destructive/40 bg-destructive/10"
                            : "border-border opacity-60"
                        : isPicked
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/40 hover:bg-muted/30",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-md border text-xs font-semibold",
                        feedback
                          ? isCorrect
                            ? "border-[color:var(--success)]/50 bg-[color:var(--success)]/20 text-[color:var(--success)]"
                            : isWrong
                              ? "border-destructive/50 bg-destructive/20 text-destructive"
                              : "border-border bg-muted text-muted-foreground"
                          : isPicked
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border bg-muted text-muted-foreground group-hover:border-primary/40",
                      )}
                    >
                      {i + 1}
                    </span>
                    <span className="flex-1 font-study text-base leading-relaxed text-foreground">
                      {c.text}
                    </span>
                    {feedback && isCorrect && (
                      <CheckCircle2
                        className="size-4 shrink-0 text-[color:var(--success)]"
                        strokeWidth={1.5}
                      />
                    )}
                    {feedback && isWrong && (
                      <XCircle
                        className="size-4 shrink-0 text-destructive"
                        strokeWidth={1.5}
                      />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Explanation */}
            {feedback?.explanation && (
              <div className="rounded-lg border-l-2 border-primary/40 bg-muted/30 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wider text-primary">
                  Explanation
                </p>
                <p className="mt-1 font-study text-sm text-foreground">
                  {feedback.explanation}
                </p>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between pt-4">
              <span className="text-xs text-muted-foreground">
                Score so far: <span className="font-medium text-foreground">{score}</span> /{" "}
                {total}
                <span className="ml-3 text-muted-foreground/60">
                  Press 1–4 to pick · F to flag · Enter to advance
                </span>
              </span>
              {(feedback || isAlreadyAnswered) && (
                <Button onClick={onNext} disabled={completing}>
                  {completing ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" /> Finishing…
                    </>
                  ) : isLast ? (
                    "Finish quiz"
                  ) : (
                    "Next question"
                  )}
                </Button>
              )}
            </div>
          </div>
        </main>

        {/* Question map drawer */}
        {mapOpen && (
          <aside className="w-72 shrink-0 overflow-y-auto border-l border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <h3 className="text-sm font-medium text-foreground">Question map</h3>
              <button
                onClick={() => setMapOpen(false)}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                aria-label="Close map"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="grid grid-cols-5 gap-2 p-4">
              {session.questions.map((q, i) => {
                const answered = answeredIds.has(q.id);
                const isFlagged = flagged.has(q.id);
                const isCurrent = i === currentIdx;
                return (
                  <button
                    key={q.id}
                    onClick={() => {
                      setCurrentIdx(i);
                      setMapOpen(false);
                    }}
                    className={cn(
                      "relative flex aspect-square items-center justify-center rounded-md border text-xs font-semibold transition-colors",
                      isCurrent
                        ? "border-primary bg-primary text-primary-foreground"
                        : answered
                          ? "border-[color:var(--success)]/40 bg-[color:var(--success)]/10 text-[color:var(--success)]"
                          : "border-border bg-muted text-muted-foreground hover:border-foreground",
                    )}
                  >
                    {i + 1}
                    {isFlagged && (
                      <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-[color:var(--warning)]" />
                    )}
                  </button>
                );
              })}
            </div>
            <div className="border-t border-border p-4">
              {!allAnswered && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={completeAndGo}
                  disabled={completing}
                >
                  {completing ? "Submitting…" : "Submit early"}
                </Button>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
