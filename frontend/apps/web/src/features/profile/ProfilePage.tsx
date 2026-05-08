import { useNavigate, useParams } from "react-router";
import {
  Award,
  BookOpen,
  Flame,
  GraduationCap,
  Inbox,
  Sparkles,
  Trophy,
} from "lucide-react";
import { useUsersGetProfile } from "@/api/generated/endpoints/users/users";
import { useAuthStore } from "@/features/auth/auth.store";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { StatTile } from "@/components/design/StatTile";
import { EmptyState } from "@/components/design";

const BADGE_ICONS: Record<string, typeof Trophy> = {
  first_quiz: Sparkles,
  active_learner: BookOpen,
  streak_starter: Flame,
  week_warrior: Flame,
  first_contribution: Inbox,
  top_contributor: Award,
  perfect_score: Trophy,
};

export default function ProfilePage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const targetId = id ?? user?.id ?? "";
  const isOwnProfile = !id || id === user?.id;

  const { data, isLoading, error } = useUsersGetProfile(targetId, {
    query: { enabled: !!user && !!targetId },
  });

  if (!user) {
    navigate("/login");
    return null;
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-[14px]" />
        <div className="grid gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-[14px]" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center text-sm text-destructive">
        Failed to load profile.
      </div>
    );
  }

  const initials = data.full_name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const accuracyPct = Math.round((data.accuracy_avg ?? 0) * 100);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        eyebrow="Profile"
        title={isOwnProfile ? "Your profile" : data.full_name}
        description="Public stats, contributions, and badges."
      />

      {/* Identity card */}
      <div className="flex flex-col gap-6 rounded-[14px] border border-border bg-card p-6 sm:flex-row sm:items-center">
        <div className="flex size-20 shrink-0 items-center justify-center rounded-full bg-primary/15 text-2xl font-semibold text-primary">
          {initials}
        </div>
        <div className="flex-1 space-y-1">
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            {data.full_name}
          </h2>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <GraduationCap className="size-3.5" strokeWidth={1.5} />
            {data.college} · Year {data.academic_year}
          </p>
          <p className="text-xs text-muted-foreground">
            Joined {new Date(data.joined_at).toLocaleDateString()} ·{" "}
            {data.enrolled_subject_count} subject
            {data.enrolled_subject_count === 1 ? "" : "s"}
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Streak"
          value={data.streak_days}
          hint={
            data.streak_days
              ? `${data.streak_days === 1 ? "1 day" : `${data.streak_days} days`}`
              : "No active streak"
          }
          icon={Flame}
          accent="warning"
        />
        <StatTile
          label="Accuracy"
          value={`${accuracyPct}%`}
          hint={`${data.correct_count} of ${data.total_attempts} correct`}
          icon={Trophy}
          accent="success"
        />
        <StatTile
          label="Quizzes"
          value={data.completed_quizzes}
          hint="Completed"
          icon={BookOpen}
          accent="primary"
        />
        <StatTile
          label="Contributions"
          value={data.published_question_count}
          hint={`${data.published_question_set_count} question set${data.published_question_set_count === 1 ? "" : "s"}`}
          icon={Sparkles}
          accent="primary"
        />
      </section>

      {/* Badges */}
      <section className="space-y-3">
        <h3 className="text-base font-medium text-foreground">Badges</h3>
        {data.badges.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.badges.map((b) => {
              const Icon = BADGE_ICONS[b.key] ?? Award;
              return (
                <div
                  key={b.key}
                  className="flex items-start gap-3 rounded-[14px] border border-border bg-card p-4"
                >
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="size-4 text-primary" strokeWidth={1.5} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{b.label}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {b.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            icon={Award}
            title="No badges yet"
            description="Complete a quiz, build a streak, or publish a question set to earn your first badge."
          />
        )}
      </section>

      {/* Recent published sets (contributions) */}
      <section className="space-y-3">
        <h3 className="text-base font-medium text-foreground">Recent contributions</h3>
        {data.recent_published_sets.length > 0 ? (
          <div className="space-y-2">
            {data.recent_published_sets.map((qs) => (
              <button
                key={qs.question_set_id}
                onClick={() => navigate(`/subjects/${qs.subject_id}`)}
                className="group flex w-full items-center gap-3 rounded-[14px] border border-border bg-card p-4 text-left transition-colors hover:border-ring/40"
              >
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Sparkles className="size-4 text-primary" strokeWidth={1.5} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-1 text-sm font-medium text-foreground group-hover:text-primary">
                    {qs.title}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {qs.subject_code} · {qs.question_count} questions ·{" "}
                    {new Date(qs.published_at).toLocaleDateString()}
                  </p>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="No published question sets yet"
            description={
              isOwnProfile
                ? "Upload material and publish your first question set to start contributing."
                : "This user hasn't published anything yet."
            }
          />
        )}
      </section>
    </div>
  );
}
