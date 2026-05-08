import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";
import { AppShell } from "./shell/AppShell";
import { ProtectedRoute } from "./ProtectedRoute";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/features/auth/auth.store";

// Public pages
const LandingPage = lazy(() => import("@/features/landing/LandingPage"));
const LoginPage = lazy(() => import("@/features/auth/LoginPage"));
const RegisterPage = lazy(() => import("@/features/auth/RegisterPage"));
const ForgotPasswordPage = lazy(() => import("@/features/auth/ForgotPasswordPage"));

// Protected pages
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage"));
const SubjectsPage = lazy(() => import("@/features/subjects/SubjectsPage"));
const UploadPage = lazy(() => import("@/features/uploads/UploadPage"));
const DraftsListPage = lazy(
  () => import("@/features/question-sets/DraftsListPage"),
);
const ReviewPage = lazy(() => import("@/features/question-sets/ReviewPage"));
const QuizStartPage = lazy(() => import("@/features/quizzes/QuizStartPage"));
const QuizPlayerPage = lazy(() => import("@/features/quizzes/QuizPlayerPage"));
const QuizResultPage = lazy(() => import("@/features/quizzes/QuizResultPage"));
const QuizHistoryPage = lazy(() => import("@/features/quizzes/QuizHistoryPage"));
const ProfilePage = lazy(() => import("@/features/profile/ProfilePage"));
const SettingsPage = lazy(() => import("@/features/settings/SettingsPage"));
const SubjectDetailPage = lazy(
  () => import("@/features/subjects/SubjectDetailPage"),
);

// Dev only
const ComponentsShowcasePage = lazy(
  () => import("@/features/dev/ComponentsShowcasePage"),
);

function PageFallback() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Root — landing for visitors, dashboard for authed users */}
        <Route path="/" element={<RootRoute />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {/* Protected — all wrapped in AppShell */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/subjects" element={<SubjectsPage />} />
          <Route path="/subjects/:id" element={<SubjectDetailPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/drafts" element={<DraftsListPage />} />
          <Route path="/drafts/:id" element={<ReviewPage />} />
          <Route path="/quiz" element={<QuizStartPage />} />
          <Route path="/quiz/:id" element={<QuizPlayerPage />} />
          <Route path="/quiz/:id/result" element={<QuizResultPage />} />
          <Route path="/history" element={<QuizHistoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/users/:id" element={<ProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route
            path="/support"
            element={<PlaceholderPage title="Support" />}
          />
        </Route>

        {/* Dev */}
        {import.meta.env.DEV && (
          <Route
            path="/dev/components"
            element={<ComponentsShowcasePage />}
          />
        )}

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function RootRoute() {
  const accessToken = useAuthStore((s) => s.accessToken);
  if (accessToken) return <Navigate to="/dashboard" replace />;
  return <LandingPage />;
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        Coming soon
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
        {title}
      </h1>
      <p className="mt-3 text-sm text-muted-foreground">
        This page is being built in a future phase.
      </p>
    </div>
  );
}
