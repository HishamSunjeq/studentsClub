import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { useAuthStore } from "@/features/auth/auth.store";
import {
  deactivateQuestion,
  fetchQuestionSet,
  publishQuestionSet,
  rejectQuestionSet,
  type Question,
} from "@/features/question-sets/question-sets.api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const DIFF_STYLES: Record<string, string> = {
  easy: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  medium: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  hard: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
};

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  if (!user) {
    navigate("/login");
    return null;
  }
  if (!id) {
    navigate("/drafts");
    return null;
  }

  const { data: qs, isLoading, error } = useQuery({
    queryKey: ["question-set", id],
    queryFn: () => fetchQuestionSet(id),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["question-set", id] });
    queryClient.invalidateQueries({ queryKey: ["question-sets/me"] });
  }

  const publishMutation = useMutation({
    mutationFn: () => publishQuestionSet(id!),
    onSuccess: () => {
      toast.success("Published");
      invalidate();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? "Failed to publish");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectQuestionSet(id!),
    onSuccess: () => {
      toast.success("Rejected");
      invalidate();
    },
    onError: () => toast.error("Failed to reject"),
  });

  const deactivateMutation = useMutation({
    mutationFn: (questionId: string) => deactivateQuestion(questionId),
    onSuccess: () => {
      toast.success("Question removed");
      invalidate();
    },
    onError: () => toast.error("Failed to remove"),
  });

  if (isLoading) {
    return <p className="p-8 text-sm text-muted-foreground">Loading…</p>;
  }
  if (error || !qs) {
    return <p className="p-8 text-sm text-destructive">Failed to load.</p>;
  }

  const activeCount = qs.questions.filter((q) => q.is_active).length;
  const isDraft = qs.status === "draft";

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate("/drafts")}>← Drafts</Button>
          <span className="text-xs font-medium px-2 py-1 rounded bg-muted">
            {qs.status.toUpperCase()}
          </span>
        </div>

        <div>
          <h1 className="text-2xl font-bold">{qs.title}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {qs.ai_model} · {qs.tokens_used.toLocaleString()} tokens · {activeCount} active questions
          </p>
        </div>

        {isDraft && (
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending || activeCount === 0}
            >
              Publish
            </Button>
            <Button
              variant="outline"
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending}
            >
              Reject set
            </Button>
            {activeCount === 0 && (
              <p className="text-xs text-destructive self-center">
                Need at least one active question to publish.
              </p>
            )}
          </div>
        )}

        <div className="space-y-4">
          {qs.questions.map((q) => (
            <QuestionCard
              key={q.id}
              q={q}
              isDraft={isDraft}
              onDeactivate={() => deactivateMutation.mutate(q.id)}
              disabled={deactivateMutation.isPending}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function QuestionCard({
  q,
  isDraft,
  onDeactivate,
  disabled,
}: {
  q: Question;
  isDraft: boolean;
  onDeactivate: () => void;
  disabled: boolean;
}) {
  return (
    <Card className={q.is_active ? "" : "opacity-50"}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-base font-medium">
              {q.position + 1}. {q.text}
            </CardTitle>
            <CardDescription className="mt-1 flex gap-2 items-center">
              <span className={`text-xs px-2 py-0.5 rounded ${DIFF_STYLES[q.difficulty]}`}>
                {q.difficulty}
              </span>
              {!q.is_active && <span className="text-xs">(removed)</span>}
            </CardDescription>
          </div>
          {isDraft && q.is_active && (
            <Button size="sm" variant="ghost" onClick={onDeactivate} disabled={disabled}>
              Remove
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <ul className="space-y-1 text-sm">
          {q.choices.map((c) => (
            <li
              key={c.id}
              className={`px-3 py-2 rounded border ${
                c.is_correct ? "border-emerald-500/50 bg-emerald-500/5" : "border-border"
              }`}
            >
              {c.is_correct && <span className="text-emerald-600 mr-2">✓</span>}
              {c.text}
            </li>
          ))}
        </ul>
        {q.explanation && (
          <div className="text-xs text-muted-foreground border-l-2 border-muted pl-3">
            <span className="font-medium">Explanation: </span>
            {q.explanation}
          </div>
        )}
        {q.source_excerpt && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Source excerpt</summary>
            <p className="mt-1 italic">{q.source_excerpt}</p>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
