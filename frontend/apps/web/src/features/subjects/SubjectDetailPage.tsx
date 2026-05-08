import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, ChevronLeft, Trophy, Users } from "lucide-react";
import {
  getSubjectsListMineQueryKey,
  useSubjectsEnroll,
  useSubjectsGet,
  useSubjectsGetLeaderboard,
  useSubjectsGetMembers,
  useSubjectsGetPublishedSets,
  useSubjectsGetTopContributors,
  useSubjectsListMine,
  useSubjectsUnenroll,
} from "@/api/generated/endpoints/subjects/subjects";
import { useAuthStore } from "@/features/auth/auth.store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

export default function SubjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [membersPage, setMembersPage] = useState(1);
  const [setsPage, setSetsPage] = useState(1);

  const { data: subject, isLoading: loadingSubject } = useSubjectsGet(
    id ?? "",
    { query: { enabled: !!id } },
  );

  const { data: myData } = useSubjectsListMine(
    { size: 200 },
    { query: { enabled: !!user } },
  );
  const enrolledIds = new Set(myData?.items.map((s) => s.id) ?? []);
  const enrolled = !!id && enrolledIds.has(id);

  const enrollMutation = useSubjectsEnroll({
    mutation: {
      onSuccess: () => {
        void queryClient.invalidateQueries({
          queryKey: getSubjectsListMineQueryKey(),
        });
      },
    },
  });
  const unenrollMutation = useSubjectsUnenroll({
    mutation: {
      onSuccess: () => {
        void queryClient.invalidateQueries({
          queryKey: getSubjectsListMineQueryKey(),
        });
      },
    },
  });

  const { data: membersData, isLoading: loadingMembers } = useSubjectsGetMembers(
    id ?? "",
    { page: membersPage, size: 20 },
    { query: { enabled: !!id } },
  );

  const { data: contributors, isLoading: loadingContributors } =
    useSubjectsGetTopContributors(
      id ?? "",
      { limit: 10 },
      { query: { enabled: !!id } },
    );

  const { data: setsData, isLoading: loadingSets } = useSubjectsGetPublishedSets(
    id ?? "",
    { page: setsPage, size: 20 },
    { query: { enabled: !!id } },
  );

  const { data: leaderboard, isLoading: loadingLeaderboard } =
    useSubjectsGetLeaderboard(
      id ?? "",
      { limit: 10 },
      { query: { enabled: !!id } },
    );

  function handleEnrollToggle() {
    if (!user) {
      navigate(`/login?next=/subjects/${id}`);
      return;
    }
    if (enrolled) {
      unenrollMutation.mutate({ subjectId: id! });
    } else {
      enrollMutation.mutate({ subjectId: id! });
    }
  }

  const mutating = enrollMutation.isPending || unenrollMutation.isPending;

  if (loadingSubject) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (!subject) {
    return (
      <div className="mx-auto max-w-4xl text-center">
        <p className="text-muted-foreground">Subject not found.</p>
        <Button
          variant="ghost"
          className="mt-4"
          onClick={() => navigate("/subjects")}
        >
          ← Back to Subjects
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Back link */}
      <button
        onClick={() => navigate("/subjects")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronLeft className="size-4" />
        Subjects
      </button>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="font-mono text-primary border-primary/30 bg-primary/10">
              {subject.code}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {subject.college} · Year {subject.academic_year}
            </span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {subject.name}
          </h1>
          {subject.description && (
            <p className="text-sm text-muted-foreground max-w-2xl">
              {subject.description}
            </p>
          )}
          <div className="flex items-center gap-4 pt-1">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Users className="size-3.5" />
              {(subject.member_count ?? 0).toLocaleString()} members
            </span>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <BookOpen className="size-3.5" />
              {subject.published_question_set_count} sets
            </span>
          </div>
        </div>
        <Button
          onClick={handleEnrollToggle}
          disabled={mutating}
          variant={enrolled ? "outline" : "default"}
          className="shrink-0"
        >
          {enrolled ? "Unenrol" : "Enrol"}
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="sets">Question Sets</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
        </TabsList>

        {/* Overview tab */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-surface-low border border-border rounded-xl p-5 text-center">
              <p className="text-2xl font-semibold text-foreground">
                {(subject.member_count ?? 0).toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Members</p>
            </div>
            <div className="bg-surface-low border border-border rounded-xl p-5 text-center">
              <p className="text-2xl font-semibold text-foreground">
                {subject.published_question_set_count}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Question Sets
              </p>
            </div>
            <div className="bg-surface-low border border-border rounded-xl p-5 text-center">
              <p className="text-2xl font-semibold text-foreground">
                {(subject.question_count ?? 0).toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Questions</p>
            </div>
          </div>

          {/* Top Contributors */}
          <div>
            <h2 className="text-base font-medium text-foreground mb-3">
              Top Contributors
            </h2>
            {loadingContributors ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 rounded-lg" />
                ))}
              </div>
            ) : !contributors?.length ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No contributors yet.
              </p>
            ) : (
              <div className="space-y-2">
                {contributors.map((c, idx) => (
                  <div
                    key={c.user_id}
                    className="flex items-center justify-between bg-surface-low border border-border rounded-lg px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-muted-foreground w-5 text-right">
                        {idx + 1}
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {c.full_name}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {c.question_set_count}{" "}
                      {c.question_set_count === 1 ? "set" : "sets"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Question Sets tab */}
        <TabsContent value="sets" className="mt-6 space-y-3">
          {loadingSets ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))
          ) : !setsData?.items.length ? (
            <p className="text-sm text-muted-foreground py-10 text-center">
              No published question sets yet.
            </p>
          ) : (
            <>
              {setsData.items.map((qs) => (
                <div
                  key={qs.id}
                  className="flex items-center justify-between bg-surface-low border border-border rounded-lg px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {qs.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {qs.question_count} questions ·{" "}
                      {new Date(qs.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(`/quiz?set=${qs.id}`)}
                  >
                    Practice
                  </Button>
                </div>
              ))}
              {(setsData.pages ?? 1) > 1 && (
                <div className="flex items-center justify-center gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={setsPage === 1}
                    onClick={() => setSetsPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {setsPage} / {setsData.pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={setsPage === setsData.pages}
                    onClick={() => setSetsPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* Members tab */}
        <TabsContent value="members" className="mt-6 space-y-3">
          {loadingMembers ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))
          ) : !membersData?.items.length ? (
            <p className="text-sm text-muted-foreground py-10 text-center">
              No members yet. Be the first to enrol!
            </p>
          ) : (
            <>
              {membersData.items.map((m) => (
                <div
                  key={m.user_id}
                  className="flex items-center justify-between bg-surface-low border border-border rounded-lg px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {m.full_name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {m.college} · Year {m.academic_year}
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(m.enrolled_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
              {(membersData.pages ?? 1) > 1 && (
                <div className="flex items-center justify-center gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={membersPage === 1}
                    onClick={() => setMembersPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {membersPage} / {membersData.pages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={membersPage === membersData.pages}
                    onClick={() => setMembersPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* Leaderboard tab */}
        <TabsContent value="leaderboard" className="mt-6 space-y-3">
          {loadingLeaderboard ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))
          ) : !leaderboard?.length ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
              <Trophy className="size-10 text-muted-foreground/40" />
              <p className="text-sm font-medium text-foreground">
                No leaderboard data yet
              </p>
              <p className="max-w-xs text-xs text-muted-foreground">
                Once members complete quizzes or publish question sets, they'll
                appear here.
              </p>
            </div>
          ) : (
            leaderboard.map((entry, idx) => {
              const accuracyPct = Math.round((entry.accuracy_avg ?? 0) * 100);
              const isPodium = idx < 3;
              return (
                <button
                  key={entry.user_id}
                  onClick={() => navigate(`/users/${entry.user_id}`)}
                  className="group flex w-full items-center gap-4 rounded-lg border border-border bg-surface-low px-4 py-3 text-left transition-colors hover:border-ring/40"
                >
                  <span
                    className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      isPodium
                        ? idx === 0
                          ? "bg-[color:var(--warning)]/20 text-[color:var(--warning)]"
                          : idx === 1
                            ? "bg-muted text-foreground"
                            : "bg-[color:var(--success)]/15 text-[color:var(--success)]"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {idx + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                      {entry.full_name}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {entry.completed_quizzes} quiz
                      {entry.completed_quizzes === 1 ? "" : "zes"} ·{" "}
                      {accuracyPct}% accuracy · {entry.contributions} contribution
                      {entry.contributions === 1 ? "" : "s"}
                    </p>
                  </div>
                  <span className="rounded-md bg-primary/10 px-2 py-1 text-[10px] font-mono font-semibold text-primary">
                    {entry.score}
                  </span>
                </button>
              );
            })
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
