import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import {
  ChevronLeft,
  CircleDot,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
} from "lucide-react";
import {
  getQuestionSetsGetQueryKey,
  getQuestionSetsListMineQueryKey,
  useQuestionSetsGet,
  useQuestionSetsPublish,
  useQuestionSetsReject,
} from "@/api/generated/endpoints/question-sets/question-sets";
import {
  useQuestionsDeactivate,
  useQuestionsRegenerate,
  useQuestionsUpdate,
} from "@/api/generated/endpoints/questions/questions";
import type {
  QuestionDifficulty,
  QuestionResponse,
} from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const DIFFICULTY_OPTIONS: { value: QuestionDifficulty; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const DIFFICULTY_TONE: Record<QuestionDifficulty, string> = {
  easy: "border-[color:var(--success)]/30 text-[color:var(--success)] data-[on=true]:bg-[color:var(--success)]/15",
  medium:
    "border-[color:var(--warning)]/30 text-[color:var(--warning)] data-[on=true]:bg-[color:var(--warning)]/15",
  hard: "border-destructive/30 text-destructive data-[on=true]:bg-destructive/15",
};

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const { data: qs, isLoading } = useQuestionSetsGet(id ?? "", {
    query: { enabled: !!user && !!id },
  });

  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null);

  // Pick the first active question by default
  useEffect(() => {
    if (qs && !activeQuestionId) {
      const first = qs.questions.find((q) => q.is_active) ?? qs.questions[0];
      if (first) setActiveQuestionId(first.id);
    }
  }, [qs, activeQuestionId]);

  function invalidate() {
    void queryClient.invalidateQueries({
      queryKey: getQuestionSetsGetQueryKey(id!),
    });
    void queryClient.invalidateQueries({
      queryKey: getQuestionSetsListMineQueryKey(),
    });
  }

  const publishMutation = useQuestionSetsPublish({
    mutation: {
      onSuccess: () => {
        toast.success("Question set published");
        invalidate();
      },
      onError: (err: { response?: { data?: { detail?: string } } }) => {
        toast.error(err.response?.data?.detail ?? "Failed to publish");
      },
    },
  });

  const rejectMutation = useQuestionSetsReject({
    mutation: {
      onSuccess: () => {
        toast.success("Question set rejected");
        invalidate();
      },
      onError: () => toast.error("Failed to reject"),
    },
  });

  if (!user) {
    navigate("/login");
    return null;
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full rounded-[14px]" />
      </div>
    );
  }

  if (!qs) {
    return (
      <div className="text-center text-muted-foreground">
        Question set not found.
        <div className="mt-4">
          <Button variant="outline" onClick={() => navigate("/drafts")}>
            Back to drafts
          </Button>
        </div>
      </div>
    );
  }

  const activeQuestion =
    qs.questions.find((q) => q.id === activeQuestionId) ?? qs.questions[0];
  const activeCount = qs.questions.filter((q) => q.is_active).length;
  const isDraft = qs.status === "draft";

  return (
    <div className="-mx-6 -my-8 flex h-[calc(100vh-3.5rem)] flex-col md:-mx-6 md:-my-8">
      {/* Top breadcrumb / status row */}
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-card px-6 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/drafts")}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-3.5" />
            Drafts
          </button>
          <span className="text-muted-foreground">/</span>
          <h1 className="truncate text-sm font-medium text-foreground">
            {qs.title}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
              isDraft
                ? "border-[color:var(--warning)]/30 bg-[color:var(--warning)]/10 text-[color:var(--warning)]"
                : qs.status === "published"
                  ? "border-[color:var(--success)]/30 bg-[color:var(--success)]/10 text-[color:var(--success)]"
                  : "border-destructive/30 bg-destructive/10 text-destructive",
            )}
          >
            {qs.status}
          </span>
          <span className="text-xs text-muted-foreground">
            {activeCount} / {qs.questions.length} active
          </span>
        </div>
      </div>

      {/* 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left rail — question list */}
        <aside className="hidden w-64 shrink-0 overflow-y-auto border-r border-border bg-card lg:block">
          <ul className="space-y-1 p-3">
            {qs.questions.map((q, i) => (
              <li key={q.id}>
                <button
                  onClick={() => setActiveQuestionId(q.id)}
                  className={cn(
                    "flex w-full items-start gap-3 rounded-lg p-3 text-left transition-colors",
                    activeQuestionId === q.id
                      ? "bg-muted"
                      : "hover:bg-muted/50",
                    !q.is_active && "opacity-50",
                  )}
                >
                  <span
                    className={cn(
                      "flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                      activeQuestionId === q.id
                        ? "bg-primary/15 text-primary"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {i + 1}
                  </span>
                  <span
                    className={cn(
                      "line-clamp-2 flex-1 text-xs",
                      activeQuestionId === q.id
                        ? "text-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    {q.text || "(empty)"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Center — editor */}
        <section className="flex-1 overflow-y-auto bg-background">
          {activeQuestion ? (
            <QuestionEditor
              key={activeQuestion.id}
              question={activeQuestion}
              isDraft={isDraft}
              questionNumber={
                qs.questions.findIndex((q) => q.id === activeQuestion.id) + 1
              }
              onSaved={invalidate}
            />
          ) : (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No questions in this set.
            </div>
          )}
        </section>

        {/* Right rail — source excerpt */}
        <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-border bg-card xl:block">
          <div className="sticky top-0 border-b border-border bg-card px-5 py-3">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Source context
            </p>
          </div>
          <div className="p-5">
            {activeQuestion?.source_excerpt ? (
              <p className="font-study text-sm text-muted-foreground">
                {activeQuestion.source_excerpt}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">
                No source excerpt available for this question.
              </p>
            )}
          </div>
        </aside>
      </div>

      {/* Sticky bottom action bar */}
      {isDraft && (
        <div className="flex shrink-0 items-center justify-between gap-3 border-t border-border bg-card px-6 py-3">
          <p className="text-xs text-muted-foreground">
            Review each question, regenerate where needed, then publish to your
            subject's question bank.
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              onClick={() => rejectMutation.mutate({ qsId: id! })}
              disabled={rejectMutation.isPending}
            >
              Reject set
            </Button>
            <Button
              onClick={() => publishMutation.mutate({ qsId: id! })}
              disabled={publishMutation.isPending || activeCount === 0}
            >
              {publishMutation.isPending ? "Publishing…" : "Publish set"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function QuestionEditor({
  question,
  isDraft,
  questionNumber,
  onSaved,
}: {
  question: QuestionResponse;
  isDraft: boolean;
  questionNumber: number;
  onSaved: () => void;
}) {
  // Local editor state — mutations flush to server.
  const [text, setText] = useState(question.text);
  const [explanation, setExplanation] = useState(question.explanation ?? "");
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>(
    question.difficulty,
  );
  const [choices, setChoices] = useState(
    question.choices.map((c) => ({ ...c })),
  );

  const updateMutation = useQuestionsUpdate({
    mutation: {
      onSuccess: () => {
        toast.success("Saved");
        onSaved();
      },
      onError: (err: { response?: { data?: { detail?: string } } }) => {
        toast.error(err.response?.data?.detail ?? "Failed to save");
      },
    },
  });
  const regenerateMutation = useQuestionsRegenerate({
    mutation: {
      onSuccess: () => {
        toast.success("Regenerated");
        onSaved();
      },
      onError: () => toast.error("Regenerate failed"),
    },
  });
  const deactivateMutation = useQuestionsDeactivate({
    mutation: {
      onSuccess: () => {
        toast.success("Question removed");
        onSaved();
      },
      onError: () => toast.error("Failed to remove"),
    },
  });

  const correctIdx = choices.findIndex((c) => c.is_correct);

  const isDirty = useMemo(() => {
    if (text !== question.text) return true;
    if ((explanation || null) !== (question.explanation || null)) return true;
    if (difficulty !== question.difficulty) return true;
    if (choices.length !== question.choices.length) return true;
    for (let i = 0; i < choices.length; i++) {
      if (choices[i].text !== question.choices[i].text) return true;
      if (choices[i].is_correct !== question.choices[i].is_correct) return true;
    }
    return false;
  }, [text, explanation, difficulty, choices, question]);

  function setCorrect(idx: number) {
    setChoices((cs) => cs.map((c, i) => ({ ...c, is_correct: i === idx })));
  }

  function setChoiceText(idx: number, value: string) {
    setChoices((cs) => cs.map((c, i) => (i === idx ? { ...c, text: value } : c)));
  }

  function save() {
    updateMutation.mutate({
      questionId: question.id,
      data: {
        text,
        explanation: explanation || null,
        difficulty,
        choices: choices.map((c) => ({ text: c.text, is_correct: c.is_correct })),
      },
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-primary/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-primary">
            Question {questionNumber}
          </span>
          <span className="flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
            <Sparkles className="size-3" />
            AI Draft
          </span>
        </div>
        {isDraft && question.is_active && (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => regenerateMutation.mutate({ questionId: question.id })}
              disabled={regenerateMutation.isPending}
            >
              {regenerateMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RotateCcw className="size-3.5" strokeWidth={1.5} />
              )}
              Regenerate
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive"
              onClick={() => deactivateMutation.mutate({ questionId: question.id })}
              disabled={deactivateMutation.isPending}
            >
              <Trash2 className="size-3.5" strokeWidth={1.5} />
              Remove
            </Button>
          </div>
        )}
      </div>

      {/* Question stem */}
      <div className="space-y-2">
        <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Question stem
        </label>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!isDraft || !question.is_active}
          rows={3}
          className="font-study text-base leading-relaxed"
        />
      </div>

      {/* Choices */}
      <div className="space-y-3">
        <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Answer choices · select one as correct
        </label>
        <div className="space-y-2">
          {choices.map((choice, i) => {
            const isCorrect = i === correctIdx;
            return (
              <div
                key={choice.id ?? i}
                className={cn(
                  "flex items-start gap-3 rounded-lg border p-3 transition-colors",
                  isCorrect
                    ? "border-[color:var(--success)]/40 bg-[color:var(--success)]/5"
                    : "border-border bg-card",
                )}
              >
                <button
                  type="button"
                  onClick={() => setCorrect(i)}
                  disabled={!isDraft || !question.is_active}
                  aria-label={isCorrect ? "Correct answer" : "Mark as correct"}
                  className={cn(
                    "mt-1 flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                    isCorrect
                      ? "border-[color:var(--success)] bg-[color:var(--success)]"
                      : "border-border hover:border-primary",
                  )}
                >
                  {isCorrect && (
                    <CircleDot className="size-3 text-white" strokeWidth={2} />
                  )}
                </button>
                <Textarea
                  value={choice.text}
                  onChange={(e) => setChoiceText(i, e.target.value)}
                  disabled={!isDraft || !question.is_active}
                  rows={1}
                  className="resize-none border-0 bg-transparent p-0 font-study text-sm shadow-none focus-visible:ring-0"
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Explanation */}
      <div className="space-y-2">
        <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Explanation (shown after answer)
        </label>
        <Textarea
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          disabled={!isDraft || !question.is_active}
          rows={2}
          placeholder="Why is the correct answer correct?"
        />
      </div>

      {/* Difficulty */}
      <div className="space-y-2">
        <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Difficulty
        </label>
        <div className="flex gap-2">
          {DIFFICULTY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setDifficulty(opt.value)}
              disabled={!isDraft || !question.is_active}
              data-on={difficulty === opt.value}
              className={cn(
                "rounded-full border bg-transparent px-4 py-1.5 text-xs font-medium transition-colors",
                DIFFICULTY_TONE[opt.value],
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Save bar (only when there are unsaved changes) */}
      {isDraft && question.is_active && (
        <div
          className={cn(
            "sticky bottom-0 -mx-8 flex items-center justify-between gap-3 border-t border-border bg-background/95 px-8 py-3 backdrop-blur",
            !isDirty && "pointer-events-none opacity-0",
          )}
        >
          <span className="text-xs text-muted-foreground">Unsaved changes</span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setText(question.text);
                setExplanation(question.explanation ?? "");
                setDifficulty(question.difficulty);
                setChoices(question.choices.map((c) => ({ ...c })));
              }}
            >
              Discard
            </Button>
            <Button onClick={save} disabled={updateMutation.isPending} size="sm">
              {updateMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      )}

      {/* Read-only banner for non-draft sets */}
      {!isDraft && (
        <div className="rounded-lg border border-border bg-muted/40 p-4 text-xs text-muted-foreground">
          This question set is{" "}
          <span className="font-medium uppercase tracking-wider">
            {question.is_active ? "published" : "rejected"}
          </span>{" "}
          and can no longer be edited.
        </div>
      )}
    </div>
  );
}
