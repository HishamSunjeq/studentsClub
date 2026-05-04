import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import {
  quizzesComplete,
  quizzesSubmitAnswer,
  useQuizzesGetWithQuestions,
} from "@/api/generated/endpoints/quizzes/quizzes";
import type { QuizAnswerResponse, QuizSessionWithQuestionsResponse } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

interface LocationState {
  session?: QuizSessionWithQuestionsResponse;
}

export default function QuizPlayerPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const location = useLocation();
  const stateSession = (location.state as LocationState | null)?.session;

  if (!user) {
    navigate("/login");
    return null;
  }
  if (!id) {
    navigate("/quiz");
    return null;
  }

  // If we don't have the session in location.state (hard refresh, deep link),
  // fetch it. Skip the fetch when state is already populated.
  const { data: fetched, isLoading, error } = useQuizzesGetWithQuestions(id, {
    query: { enabled: !stateSession },
  });

  const session = stateSession ?? fetched;

  if (isLoading) return <p className="p-8 text-sm text-muted-foreground">Loading…</p>;
  if (error || !session) {
    return <p className="p-8 text-sm text-destructive">Failed to load quiz.</p>;
  }

  return <QuizRunner session={session} />;
}

function QuizRunner({ session }: { session: QuizSessionWithQuestionsResponse }) {
  const navigate = useNavigate();
  const total = session.questions.length;

  const answeredSet = new Set(session.answered_question_ids ?? []);
  const initialIdx = (() => {
    const i = session.questions.findIndex((q) => !answeredSet.has(q.id));
    return i === -1 ? Math.max(total - 1, 0) : i;
  })();
  const allAnswered = answeredSet.size >= total && total > 0;

  const [currentIdx, setCurrentIdx] = useState(initialIdx);
  const [pickedChoiceId, setPickedChoiceId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<QuizAnswerResponse | null>(null);
  const [score, setScore] = useState(session.score);
  const [submitting, setSubmitting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [done, setDone] = useState(session.status === "completed");

  // If the user reopens a session where every question is answered but the
  // session is still in_progress, give them a nudge to finish it.
  useEffect(() => {
    if (allAnswered && session.status === "in_progress" && !done && !completing) {
      void (async () => {
        setCompleting(true);
        try {
          await quizzesComplete(session.id);
          setDone(true);
        } catch {
          /* user can press the Finish button manually */
        } finally {
          setCompleting(false);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = session.questions[currentIdx];
  const isLast = currentIdx === total - 1;

  async function onPick(choiceId: string) {
    if (feedback || submitting) return;
    setPickedChoiceId(choiceId);
    setSubmitting(true);
    try {
      const res = await quizzesSubmitAnswer(session.id, {
        question_id: current.id,
        choice_id: choiceId,
      });
      setFeedback(res);
      setScore(res.score);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      toast.error(detail ?? "Failed to submit answer");
      setPickedChoiceId(null);
    } finally {
      setSubmitting(false);
    }
  }

  async function onNext() {
    if (isLast) {
      setCompleting(true);
      try {
        await quizzesComplete(session.id);
        setDone(true);
      } catch {
        toast.error("Failed to complete quiz");
      } finally {
        setCompleting(false);
      }
      return;
    }
    setCurrentIdx((i) => i + 1);
    setPickedChoiceId(null);
    setFeedback(null);
  }

  if (done) {
    const pct = total === 0 ? 0 : Math.round((score / total) * 100);
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Quiz complete</CardTitle>
            <CardDescription>
              You scored {score} of {total} ({pct}%)
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button onClick={() => navigate("/quiz")}>Take another quiz</Button>
            <Button variant="ghost" onClick={() => navigate("/")}>
              Home
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Edge case: nothing left to answer but completion call hasn't finished yet.
  if (!current) {
    return <p className="p-8 text-sm text-muted-foreground">Wrapping up…</p>;
  }

  const isAlreadyAnswered = answeredSet.has(current.id) && !feedback;

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Question {currentIdx + 1} of {total}
          </span>
          <span>Score: {score}</span>
        </div>

        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${((currentIdx + (feedback ? 1 : 0)) / total) * 100}%` }}
          />
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">{current.text}</CardTitle>
            <CardDescription>Difficulty: {current.difficulty}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {isAlreadyAnswered && (
              <p className="text-xs text-muted-foreground">
                You already answered this question. Skip ahead.
              </p>
            )}
            {current.choices.map((c) => {
              const isPicked = pickedChoiceId === c.id;
              const isCorrect = feedback && c.id === feedback.correct_choice_id;
              const isWrongPick = feedback && isPicked && !feedback.is_correct;
              const cls = feedback
                ? isCorrect
                  ? "border-emerald-500 bg-emerald-500/10"
                  : isWrongPick
                  ? "border-rose-500 bg-rose-500/10"
                  : "border-border opacity-60"
                : isPicked
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50";
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onPick(c.id)}
                  disabled={!!feedback || submitting || isAlreadyAnswered}
                  className={`w-full text-left px-3 py-2 rounded border text-sm transition-colors ${cls}`}
                >
                  {feedback && isCorrect && <span className="text-emerald-600 mr-2">✓</span>}
                  {feedback && isWrongPick && <span className="text-rose-600 mr-2">✗</span>}
                  {c.text}
                </button>
              );
            })}

            {feedback?.explanation && (
              <div className="text-xs text-muted-foreground border-l-2 border-muted pl-3 mt-3">
                <span className="font-medium">Explanation: </span>
                {feedback.explanation}
              </div>
            )}
          </CardContent>
        </Card>

        {(feedback || isAlreadyAnswered) && (
          <Button className="w-full" onClick={onNext} disabled={completing}>
            {completing ? "Finishing…" : isLast ? "Finish quiz" : "Next question"}
          </Button>
        )}
      </div>
    </div>
  );
}
