import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { useAuthStore } from "@/features/auth/auth.store";
import {
  enrollSubject,
  fetchMySubjects,
  fetchSubjects,
  unenrollSubject,
  type Subject,
} from "@/features/subjects/subjects.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const COLLEGES = ["Engineering", "Medicine", "Business", "Science", "Law", "Arts"];
const YEARS = [1, 2, 3, 4, 5, 6, 7];

export default function SubjectsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [college, setCollege] = useState("");
  const [academicYear, setAcademicYear] = useState<number | undefined>();
  const [page, setPage] = useState(1);

  const queryClient = useQueryClient();

  const { data: subjectsData, isLoading: loadingSubjects } = useQuery({
    queryKey: ["subjects", { college, academicYear, page }],
    queryFn: () =>
      fetchSubjects({
        college: college || undefined,
        academic_year: academicYear,
        page,
        size: 12,
      }),
  });

  const { data: myData } = useQuery({
    queryKey: ["subjects/me"],
    queryFn: () => fetchMySubjects({ size: 100 }),
    enabled: !!user,
  });

  const enrolledIds = new Set(myData?.items.map((s) => s.id) ?? []);

  const enrollMutation = useMutation({
    mutationFn: enrollSubject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["subjects/me"] });
    },
  });

  const unenrollMutation = useMutation({
    mutationFn: unenrollSubject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["subjects/me"] });
    },
  });

  function handleEnrollToggle(subject: Subject) {
    if (!user) {
      navigate("/login");
      return;
    }
    if (enrolledIds.has(subject.id)) {
      unenrollMutation.mutate(subject.id);
    } else {
      enrollMutation.mutate(subject.id);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Subjects</h1>
            <p className="text-muted-foreground mt-1">
              Browse subjects and enrol to start practising
            </p>
          </div>
          {user && (
            <Button variant="outline" onClick={() => navigate("/")}>
              ← Home
            </Button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <select
            className="h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            value={college}
            onChange={(e) => { setCollege(e.target.value); setPage(1); }}
          >
            <option value="">All colleges</option>
            {COLLEGES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            className="h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            value={academicYear ?? ""}
            onChange={(e) => {
              setAcademicYear(e.target.value ? Number(e.target.value) : undefined);
              setPage(1);
            }}
          >
            <option value="">All years</option>
            {YEARS.map((y) => (
              <option key={y} value={y}>Year {y}</option>
            ))}
          </select>
        </div>

        {/* Grid */}
        {loadingSubjects ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-xl" />
            ))}
          </div>
        ) : !subjectsData?.items.length ? (
          <p className="text-muted-foreground py-16 text-center">No subjects found.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {subjectsData.items.map((subject) => {
                const enrolled = enrolledIds.has(subject.id);
                const mutating =
                  enrollMutation.isPending || unenrollMutation.isPending;

                return (
                  <Card key={subject.id} className="flex flex-col">
                    <CardHeader className="flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <CardTitle className="text-base leading-snug">
                          {subject.name}
                        </CardTitle>
                        {enrolled && (
                          <Badge variant="secondary" className="shrink-0">
                            Enrolled
                          </Badge>
                        )}
                      </div>
                      <CardDescription>
                        {subject.college} · Year {subject.academic_year} ·{" "}
                        <span className="font-mono text-xs">{subject.code}</span>
                      </CardDescription>
                      {subject.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                          {subject.description}
                        </p>
                      )}
                    </CardHeader>
                    <CardContent>
                      <Button
                        size="sm"
                        variant={enrolled ? "outline" : "default"}
                        className="w-full"
                        disabled={mutating}
                        onClick={() => handleEnrollToggle(subject)}
                      >
                        {enrolled ? "Unenrol" : "Enrol"}
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Pagination */}
            {subjectsData.pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {page} of {subjectsData.pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === subjectsData.pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
