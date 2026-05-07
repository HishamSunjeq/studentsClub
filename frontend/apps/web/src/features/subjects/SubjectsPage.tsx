import { useState } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Search, Users } from "lucide-react";
import {
  getSubjectsListMineQueryKey,
  useSubjectsEnroll,
  useSubjectsList,
  useSubjectsListMine,
  useSubjectsUnenroll,
} from "@/api/generated/endpoints/subjects/subjects";
import type { SubjectResponse } from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Skeleton } from "@/components/ui/skeleton";

const YEAR_OPTIONS = [
  { label: "Freshman", value: 1 },
  { label: "Sophomore", value: 2 },
  { label: "Junior", value: 3 },
  { label: "Senior", value: 4 },
];

type TabFilter = "all" | "enrolled";

export default function SubjectsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<TabFilter>("all");
  const [selectedYears, setSelectedYears] = useState<Set<number>>(new Set());

  const { data: allData, isLoading } = useSubjectsList({ size: 100 });
  const { data: myData } = useSubjectsListMine(
    { size: 200 },
    { query: { enabled: !!user } },
  );

  const enrolledIds = new Set(myData?.items.map((s) => s.id) ?? []);

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

  function toggleYear(year: number) {
    setSelectedYears((prev) => {
      const next = new Set(prev);
      if (next.has(year)) next.delete(year);
      else next.add(year);
      return next;
    });
  }

  function handleEnrollToggle(e: React.MouseEvent, subject: SubjectResponse) {
    e.stopPropagation();
    if (!user) {
      navigate(`/login?next=/subjects/${subject.id}`);
      return;
    }
    if (enrolledIds.has(subject.id)) {
      unenrollMutation.mutate({ subjectId: subject.id });
    } else {
      enrollMutation.mutate({ subjectId: subject.id });
    }
  }

  const filtered = (allData?.items ?? []).filter((s) => {
    if (tab === "enrolled" && !enrolledIds.has(s.id)) return false;
    if (selectedYears.size > 0 && !selectedYears.has(s.academic_year))
      return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.code.toLowerCase().includes(q) ||
        s.college.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-8">
      {/* Page header + search */}
      <div className="space-y-5">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Subjects
        </h1>
        <div className="relative max-w-2xl">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search subjects, codes, or colleges"
            className="w-full rounded-lg border border-border bg-muted/40 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-ring focus:ring-2 focus:ring-ring/20 transition-all"
          />
        </div>
        {/* Filter chips */}
        <div className="flex flex-wrap gap-2">
          {(["all", "enrolled"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={
                tab === t
                  ? "px-4 py-1.5 rounded-full text-xs font-medium bg-primary text-primary-foreground transition-colors"
                  : "px-4 py-1.5 rounded-full text-xs font-medium bg-muted border border-border text-muted-foreground hover:bg-muted/80 transition-colors"
              }
            >
              {t === "all" ? "All Subjects" : "Enrolled"}
            </button>
          ))}
          {(["Popular", "Recent", "Exam Prep"] as const).map((label) => (
            <button
              key={label}
              className="px-4 py-1.5 rounded-full text-xs font-medium bg-muted border border-border text-muted-foreground hover:bg-muted/80 transition-colors"
              disabled
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left filter sidebar */}
        <aside className="hidden lg:block w-56 shrink-0 space-y-6">
          <div>
            <p className="text-sm font-medium text-foreground mb-3">
              Academic Year
            </p>
            <div className="space-y-2">
              {YEAR_OPTIONS.map(({ label, value }) => (
                <label
                  key={value}
                  className="flex items-center gap-2 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={selectedYears.has(value)}
                    onChange={() => toggleYear(value)}
                    className="rounded border-border bg-muted text-primary focus:ring-primary/50"
                  />
                  <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                    {label}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </aside>

        {/* Subject grid */}
        <div className="flex-1">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-52 rounded-xl" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-muted-foreground py-20 text-center text-sm">
              No subjects found.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filtered.map((subject) => {
                const enrolled = enrolledIds.has(subject.id);
                const mutating =
                  enrollMutation.isPending || unenrollMutation.isPending;

                return (
                  <div
                    key={subject.id}
                    onClick={() => navigate(`/subjects/${subject.id}`)}
                    className="bg-surface-low border border-border rounded-xl p-8 flex flex-col hover:border-ring/40 transition-colors group cursor-pointer"
                  >
                    {/* Top row: code badge + enrolled/join */}
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-xs font-medium text-primary px-2 py-1 bg-primary/10 rounded-md">
                        {subject.code}
                      </span>
                      {enrolled ? (
                        <span className="px-2 py-1 rounded-full bg-muted border border-border text-muted-foreground text-[10px] font-medium uppercase tracking-widest flex items-center gap-1">
                          <span className="size-1.5 rounded-full bg-emerald-500" />
                          Enrolled
                        </span>
                      ) : (
                        <button
                          onClick={(e) => handleEnrollToggle(e, subject)}
                          disabled={mutating}
                          className="text-xs text-foreground bg-muted border border-border rounded-full px-3 py-1 hover:bg-muted/60 transition-colors disabled:opacity-50"
                        >
                          Join
                        </button>
                      )}
                    </div>

                    {/* Title */}
                    <h2 className="text-lg font-semibold text-foreground mb-1.5 group-hover:text-primary transition-colors leading-snug">
                      {subject.name}
                    </h2>

                    {/* Description */}
                    <p className="text-sm text-muted-foreground mb-6 line-clamp-2 flex-1">
                      {subject.description ?? subject.college}
                    </p>

                    {/* Footer stats */}
                    <div className="mt-auto pt-4 border-t border-border flex items-center gap-4">
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Users className="size-3.5" />
                        <span className="text-xs">
                          {(subject.member_count ?? 0).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <BookOpen className="size-3.5" />
                        <span className="text-xs">
                          {subject.published_question_set_count} sets
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
