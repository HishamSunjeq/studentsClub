import { Navigate, Route, Routes } from "react-router";
import { useAuthStore } from "@/features/auth/auth.store";
import LoginPage from "@/features/auth/LoginPage";
import RegisterPage from "@/features/auth/RegisterPage";
import ComponentsShowcasePage from "@/features/dev/ComponentsShowcasePage";
import DraftsListPage from "@/features/question-sets/DraftsListPage";
import ReviewPage from "@/features/question-sets/ReviewPage";
import QuizPlayerPage from "@/features/quizzes/QuizPlayerPage";
import QuizStartPage from "@/features/quizzes/QuizStartPage";
import SubjectsPage from "@/features/subjects/SubjectsPage";
import UploadPage from "@/features/uploads/UploadPage";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function Home() {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>StudentsClub</CardTitle>
          <CardDescription>
            {user
              ? `Welcome, ${user.full_name}`
              : "Upload study material. Get AI-generated questions. Practice with your peers."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {user ? (
            <>
              <Button asChild>
                <a href="/subjects">Browse Subjects</a>
              </Button>
              <Button asChild variant="secondary">
                <a href="/upload">Upload Material</a>
              </Button>
              <Button asChild variant="secondary">
                <a href="/drafts">My Drafts</a>
              </Button>
              <Button asChild>
                <a href="/quiz">Take a Quiz</a>
              </Button>
              <Button variant="outline" onClick={logout}>
                Sign out
              </Button>
            </>
          ) : (
            <>
              <Button asChild>
                <a href="/register">Get Started</a>
              </Button>
              <Button variant="outline" asChild>
                <a href="/login">Sign In</a>
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/subjects" element={<SubjectsPage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/drafts" element={<DraftsListPage />} />
      <Route path="/drafts/:id" element={<ReviewPage />} />
      <Route path="/quiz" element={<QuizStartPage />} />
      <Route path="/quiz/:id" element={<QuizPlayerPage />} />
      {import.meta.env.DEV && (
        <Route path="/dev/components" element={<ComponentsShowcasePage />} />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
