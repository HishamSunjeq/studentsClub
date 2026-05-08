import { useNavigate } from "react-router";
import {
  ArrowRight,
  BookOpen,
  Compass,
  Flame,
  Inbox,
  Sparkles,
  Target,
  Trophy,
  Upload,
} from "lucide-react";
import {
  useUsersGetMeStats,
  useUsersGetMeContinue,
  useUsersGetMeRecommendedSubjects,
} from "@/api/generated/endpoints/users/users";
import { useFeedList } from "@/api/generated/endpoints/feed/feed";
import { useQuestionSetsListMine } from "@/api/generated/endpoints/question-sets/question-sets";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatTile } from "@/components/design/StatTile";
import { StreakRing } from "@/components/design/StreakRing";
import { EmptyState } from "@/components/design";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const { data: stats, isLoading: loadingStats } = useUsersGetMeStats({
    query: { enabled: !!user, staleTime: 60_000 },
  });
  const { data: continueData } = useUsersGetMeContinue({
    query: { enabled: !!user },
  });
  const { data: recommended } = useUsersGetMeRecommendedSubjects({
    query: { enabled: !!user },
  });
  const { data: feed } = useFeedList(
    { size: 6 },
    { query: { enabled: !!user } },
  );
  const { data: drafts } = useQuestionSetsListMine(
    { size: 5, status: "draft" },
    { query: { enabled: !!user } },
  );

  if (!user) {
    navigate("/login");
    return null;
  }

  const firstName = user.full_name.split(" ")[0];
  const accuracyPct = Math.round((stats?.accuracy_avg ?? 0) * 100);

  return (
    <div className="space-y-8">
      {/* Hero — greeting + streak/XP/weekly goal */}
      <section className="rounded-[14px] border border-border bg-card p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-widest text-primary">
              Welcome back
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              Good to see you, {firstName}
            </h1>
            <p className="text-sm text-muted-foreground">
              {stats && stats.streak_days > 0
                ? `You're on a ${stats.streak_days}-day streak. Keep the momentum going.`
                : "Practice today to start a new streak."}
            </p>
          </div>

          {/* Hero stats trio */}
          <div className="flex items-center gap-6 rounded-lg border border-border bg-muted/30 px-6 py-4">
            <div className="flex items-center gap-3">
              {loadingStats ? (
                <Skeleton className="size-[88px] rounded-full" />
              ) : (
                <StreakRing
                  value={stats?.streak_days ?? 0}
                  max={Math.max(7, stats?.streak_days ?? 0)}
                  size={88}
                  stroke={3}
                  label="Streak"
                  suffix="d"
                />
              )}
            </div>
            <div className="h-12 w-px bg-border" />
            <div className="flex flex-col">
              <span className="text-2xl font-semibold text-primary">
                {(stats?.xp_total ?? 0).toLocaleString()}
              </span>
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                XP earned
              </span>
            </div>
            <div className="h-12 w-px bg-border" />
            <div className="flex flex-col">
              <span className="text-2xl font-semibold text-foreground">
                {stats?.weekly_progress ?? 0}
                <span className="text-base font-medium text-muted-foreground">
                  /{stats?.weekly_goal ?? 5}
                </span>
              </span>
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Weekly quizzes
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Stat tiles row */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Streak"
          value={stats?.streak_days ?? 0}
          hint={
            stats?.streak_days
              ? `${stats.streak_days === 1 ? "1 day" : `${stats.streak_days} days`} of practice`
              : "Start practising today"
          }
          icon={Flame}
          accent="warning"
        />
        <StatTile
          label="Accuracy"
          value={`${accuracyPct}%`}
          hint={`${stats?.correct_count ?? 0} of ${stats?.total_attempts ?? 0} answered correctly`}
          icon={Trophy}
          accent="success"
        />
        <StatTile
          label="XP"
          value={(stats?.xp_total ?? 0).toLocaleString()}
          hint={`${stats?.published_question_count ?? 0} published questions`}
          icon={Sparkles}
          accent="primary"
        />
        <StatTile
          label="Drafts pending"
          value={stats?.drafts_pending_review_count ?? 0}
          hint="Awaiting your review"
          icon={Inbox}
          accent="primary"
        />
      </section>

      {/* Bento grid */}
      <section className="grid gap-4 lg:grid-cols-12">
        {/* Continue tile (span 8) */}
        <div className="lg:col-span-8">
          {continueData ? (
            <button
              onClick={() => navigate(`/quiz/${continueData.session_id}`)}
              className="group relative block w-full overflow-hidden rounded-[14px] border border-border bg-card p-8 text-left transition-colors hover:border-primary/40"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/8 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="relative space-y-6">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-widest text-primary">
                      Continue where you left off
                    </p>
                    <h2 className="mt-2 text-xl font-semibold tracking-tight text-foreground">
                      {continueData.subject_name}
                    </h2>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {continueData.subject_code} · {continueData.answered_questions}{" "}
                      / {continueData.total_questions} answered
                    </p>
                  </div>
                  <span className="rounded-md bg-primary/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-primary">
                    In progress
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span>{Math.round((continueData.progress ?? 0) * 100)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{
                        width: `${Math.round((continueData.progress ?? 0) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm font-medium text-primary">
                  Resume quiz
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
                </div>
              </div>
            </button>
          ) : (
            <div className="flex h-full flex-col justify-between rounded-[14px] border border-border bg-card p-8">
              <div className="space-y-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10">
                  <Target className="size-5 text-primary" strokeWidth={1.5} />
                </div>
                <h2 className="text-xl font-semibold tracking-tight text-foreground">
                  Start your first quiz today
                </h2>
                <p className="max-w-md text-sm text-muted-foreground">
                  Pick a subject you've enrolled in and drill the published
                  questions. Your progress carries forward automatically.
                </p>
              </div>
              <div className="mt-6">
                <Button onClick={() => navigate("/quiz")}>
                  <Sparkles className="size-3.5" strokeWidth={1.5} />
                  Start a quiz
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Drafts pending tile (span 4) */}
        <div className="lg:col-span-4">
          <div className="flex h-full flex-col rounded-[14px] border border-border bg-card p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">
                Drafts for review
              </h3>
              <button
                onClick={() => navigate("/drafts")}
                className="text-xs text-primary hover:underline"
              >
                View all
              </button>
            </div>
            {drafts && drafts.items.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {drafts.items.slice(0, 4).map((d) => (
                  <li key={d.id}>
                    <button
                      onClick={() => navigate(`/drafts/${d.id}`)}
                      className="group flex w-full items-center gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2 text-left transition-colors hover:border-ring/40"
                    >
                      <div className="flex size-7 shrink-0 items-center justify-center rounded bg-muted">
                        <Inbox
                          className="size-3.5 text-muted-foreground"
                          strokeWidth={1.5}
                        />
                      </div>
                      <span className="line-clamp-1 flex-1 text-xs text-foreground group-hover:text-primary">
                        {d.title}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-1 items-center justify-center py-6 text-center">
                <p className="text-xs text-muted-foreground">
                  No pending drafts. Upload material to get started.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Activity feed (span 8) */}
        <div className="lg:col-span-8">
          <div className="flex h-full flex-col rounded-[14px] border border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">
                Activity in your subjects
              </h3>
              {feed && feed.items.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {feed.total} updates
                </span>
              )}
            </div>
            {feed && feed.items.length > 0 ? (
              <ul className="space-y-1">
                {feed.items.map((item) => (
                  <li key={item.question_set_id}>
                    <button
                      onClick={() =>
                        navigate(`/subjects/${item.subject_id}`)
                      }
                      className="group flex w-full items-start gap-3 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-muted/50"
                    >
                      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded bg-primary/10">
                        <BookOpen
                          className="size-3.5 text-primary"
                          strokeWidth={1.5}
                        />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-1 text-xs font-medium text-foreground group-hover:text-primary">
                          {item.title}
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          {item.author_name} · {item.subject_code} ·{" "}
                          {item.question_count} questions ·{" "}
                          {timeAgo(new Date(item.published_at))}
                        </p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-1 items-center justify-center py-8">
                <EmptyState
                  icon={Compass}
                  title="No activity yet"
                  description="Enrol in a subject and your classmates' newly-published question sets will appear here."
                />
              </div>
            )}
          </div>
        </div>

        {/* Recommended subjects (span 4) */}
        <div className="lg:col-span-4">
          <div className="flex h-full flex-col rounded-[14px] border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-medium text-foreground">
              Recommended for you
            </h3>
            {recommended && recommended.length > 0 ? (
              <ul className="space-y-2">
                {recommended.slice(0, 4).map((s) => (
                  <li key={s.id}>
                    <button
                      onClick={() => navigate(`/subjects/${s.id}`)}
                      className="group flex w-full items-center gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2 text-left transition-colors hover:border-ring/40"
                    >
                      <span
                        className={cn(
                          "rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-primary",
                        )}
                      >
                        {s.code}
                      </span>
                      <span className="line-clamp-1 flex-1 text-xs text-foreground group-hover:text-primary">
                        {s.name}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">
                We'll surface subjects to enrol in once we know more about your
                program.
              </p>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="mt-auto justify-start pt-3 text-primary"
              onClick={() => navigate("/subjects")}
            >
              Browse all subjects
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </div>

        {/* Upload CTA (span 12) */}
        <div className="lg:col-span-12">
          <button
            onClick={() => navigate("/upload")}
            className="group flex w-full items-center gap-4 rounded-[14px] border border-dashed border-border bg-card p-6 text-left transition-colors hover:border-primary/40 hover:bg-muted/30"
          >
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Upload className="size-5 text-primary" strokeWidth={1.5} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">
                Upload new study material
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Drop notes, slides, or scanned exams. AI generates draft
                questions for your review.
              </p>
            </div>
            <ArrowRight
              className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground"
              strokeWidth={1.5}
            />
          </button>
        </div>
      </section>
    </div>
  );
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks}w ago`;
  return date.toLocaleDateString();
}
