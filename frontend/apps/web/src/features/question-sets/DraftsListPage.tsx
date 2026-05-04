import { useNavigate } from "react-router";
import { useQuestionSetsListMine } from "@/api/generated/endpoints/question-sets/question-sets";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  published: "Published",
  rejected: "Rejected",
};

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  published: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  rejected: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
};

export default function DraftsListPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  if (!user) {
    navigate("/login");
    return null;
  }

  const { data, isLoading, error } = useQuestionSetsListMine({ size: 50 });

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">My Question Sets</h1>
            <p className="text-sm text-muted-foreground">
              Review AI-generated drafts before publishing.
            </p>
          </div>
          <Button variant="ghost" onClick={() => navigate("/")}>← Home</Button>
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {error && <p className="text-sm text-destructive">Failed to load.</p>}
        {data?.items.length === 0 && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No question sets yet. Upload a study material to get started.
            </CardContent>
          </Card>
        )}

        <div className="space-y-3">
          {data?.items.map((qs) => (
            <Card
              key={qs.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate(`/drafts/${qs.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="truncate">{qs.title}</CardTitle>
                    <CardDescription className="text-xs mt-1">
                      {qs.ai_model} · {qs.tokens_used.toLocaleString()} tokens ·{" "}
                      {new Date(qs.created_at).toLocaleString()}
                    </CardDescription>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded ${STATUS_STYLES[qs.status]}`}
                  >
                    {STATUS_LABELS[qs.status]}
                  </span>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
