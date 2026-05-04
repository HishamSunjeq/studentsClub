import { useState } from "react";
import { useNavigate } from "react-router";
import { useSubjectsListMine } from "@/api/generated/endpoints/subjects/subjects";
import { useQuizzesStart } from "@/api/generated/endpoints/quizzes/quizzes";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export default function QuizStartPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [subjectId, setSubjectId] = useState("");
  const [count, setCount] = useState(10);

  if (!user) {
    navigate("/login");
    return null;
  }

  const { data: mySubjects } = useSubjectsListMine({ size: 100 });

  const startMutation = useQuizzesStart({
    mutation: {
      onSuccess: (session) => {
        navigate(`/quiz/${session.id}`, { state: { session } });
      },
      onError: (err: { response?: { data?: { detail?: string } } }) => {
        toast.error(err.response?.data?.detail ?? "Failed to start quiz");
      },
    },
  });

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Start a Quiz</CardTitle>
          <CardDescription>
            Pick a subject you've enrolled in and how many questions to attempt.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-1">
            <label className="text-sm font-medium">Subject</label>
            <select
              className="w-full h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
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
            {mySubjects?.items.length === 0 && (
              <p className="text-xs text-muted-foreground">
                You haven't enrolled in any subjects yet.
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Number of questions</label>
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-full h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          <Button
            className="w-full"
            disabled={!subjectId || startMutation.isPending}
            onClick={() => startMutation.mutate({ data: { subject_id: subjectId, count } })}
          >
            {startMutation.isPending ? "Starting…" : "Start quiz"}
          </Button>
          <Button variant="ghost" className="w-full" onClick={() => navigate("/")}>
            ← Back
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
