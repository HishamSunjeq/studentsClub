import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { BrainCircuit, Clock, Minus, Plus, Sparkles } from "lucide-react";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import { useQuizzesStart } from "@/api/generated/endpoints/quizzes/quizzes";
import type { QuestionDifficulty } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/design/PageHeader";
import { cn } from "@/lib/utils";

const DIFFICULTY_OPTIONS: { value: QuestionDifficulty; label: string; tone: string }[] =
  [
    { value: "easy", label: "Easy", tone: "[color:var(--success)]" },
    { value: "medium", label: "Medium", tone: "[color:var(--warning)]" },
    { value: "hard", label: "Hard", tone: "destructive" },
  ];

const COUNT_PRESETS = [5, 10, 20, 50];

export default function QuizStartPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [subjectId, setSubjectId] = useState("");
  const [count, setCount] = useState(10);
  const [difficulties, setDifficulties] = useState<QuestionDifficulty[]>([]);
  const [timed, setTimed] = useState(false);

  const { data: mySubjects } = useSubjectsListMine(
    { size: 100 },
    { query: { enabled: !!user } },
  );

  const startMutation = useQuizzesStart({
    mutation: {
      onSuccess: (session) => {
        const params = timed ? "?timed=true" : "";
        navigate(`/quiz/${session.id}${params}`, { state: { session } });
      },
      onError: (err: { response?: { data?: { detail?: string } } }) => {
        toast.error(err.response?.data?.detail ?? "Failed to start quiz");
      },
    },
  });

  function toggleDifficulty(d: QuestionDifficulty) {
    setDifficulties((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d],
    );
  }

  if (!user) {
    navigate("/login");
    return null;
  }

  const noSubjects = mySubjects && mySubjects.items.length === 0;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        eyebrow="New Quiz"
        title="Start a practice quiz"
        description="Pick a subject from the ones you've enrolled in, configure the difficulty mix and length, and start drilling."
      />

      {noSubjects ? (
        <div className="rounded-[14px] border border-border bg-card p-8 text-center">
          <BrainCircuit
            className="mx-auto size-10 text-muted-foreground/40"
            strokeWidth={1.5}
          />
          <p className="mt-4 text-sm font-medium text-foreground">
            You haven't enrolled in any subjects yet
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Browse the catalogue and enrol to start practising.
          </p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => navigate("/subjects")}
          >
            Browse subjects
          </Button>
        </div>
      ) : (
        <div className="space-y-6 rounded-[14px] border border-border bg-card p-8">
          {/* Subject */}
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Subject
            </label>
            <select
              className="h-11 w-full rounded-lg border border-border bg-muted/40 px-3 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
            >
              <option value="">— select subject —</option>
              {mySubjects?.items.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          {/* Count */}
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Number of questions
            </label>
            <div className="flex flex-wrap items-center gap-2">
              {COUNT_PRESETS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setCount(n)}
                  className={cn(
                    "rounded-full border px-4 py-1.5 text-xs font-medium transition-colors",
                    count === n
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-muted text-muted-foreground hover:bg-muted/80",
                  )}
                >
                  {n}
                </button>
              ))}
              <div className="ml-auto flex items-center gap-2 rounded-full border border-border bg-muted px-2 py-1">
                <button
                  type="button"
                  className="rounded-full p-1 text-muted-foreground hover:bg-background hover:text-foreground disabled:opacity-30"
                  onClick={() => setCount((c) => Math.max(1, c - 1))}
                  disabled={count <= 1}
                  aria-label="Decrease count"
                >
                  <Minus className="size-3" />
                </button>
                <span className="min-w-[2ch] text-center text-xs font-semibold text-foreground">
                  {count}
                </span>
                <button
                  type="button"
                  className="rounded-full p-1 text-muted-foreground hover:bg-background hover:text-foreground disabled:opacity-30"
                  onClick={() => setCount((c) => Math.min(50, c + 1))}
                  disabled={count >= 50}
                  aria-label="Increase count"
                >
                  <Plus className="size-3" />
                </button>
              </div>
            </div>
          </div>

          {/* Difficulty mix */}
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Difficulty
              <span className="ml-2 normal-case text-muted-foreground/60">
                (leave empty for any)
              </span>
            </label>
            <div className="flex gap-2">
              {DIFFICULTY_OPTIONS.map((d) => {
                const selected = difficulties.includes(d.value);
                return (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => toggleDifficulty(d.value)}
                    className={cn(
                      "rounded-full border px-4 py-1.5 text-xs font-medium transition-colors",
                      selected
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-transparent text-muted-foreground hover:bg-muted/60",
                    )}
                  >
                    {d.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Timed toggle */}
          <div className="flex items-start justify-between gap-4 rounded-lg border border-border bg-muted/40 p-4">
            <div className="flex items-start gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <Clock className="size-4 text-primary" strokeWidth={1.5} />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Timed mode</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  60 seconds per question. Adds pressure for exam practice.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setTimed((v) => !v)}
              role="switch"
              aria-checked={timed}
              className={cn(
                "relative h-6 w-11 shrink-0 rounded-full transition-colors",
                timed ? "bg-primary" : "bg-muted-foreground/30",
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 size-5 rounded-full bg-white transition-transform",
                  timed ? "translate-x-[1.375rem]" : "translate-x-0.5",
                )}
              />
            </button>
          </div>

          <Button
            size="lg"
            className="w-full"
            disabled={!subjectId || startMutation.isPending}
            onClick={() =>
              startMutation.mutate({
                data: {
                  subject_id: subjectId,
                  count,
                  difficulties: difficulties.length ? difficulties : undefined,
                },
              })
            }
          >
            <Sparkles className="size-4" strokeWidth={1.5} />
            {startMutation.isPending ? "Starting…" : "Start quiz"}
          </Button>
        </div>
      )}
    </div>
  );
}
