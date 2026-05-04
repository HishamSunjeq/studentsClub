import { Link } from "react-router";
import { BookOpen, BrainCircuit, GraduationCap, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

// Stub — full redesign in Phase 4.
export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Nav */}
      <header className="flex h-14 items-center justify-between border-b border-border px-6">
        <div className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <GraduationCap className="size-4 text-primary" strokeWidth={1.5} />
          StudentsClub
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login">Sign in</Link>
          </Button>
          <Button size="sm" asChild>
            <Link to="/register">Get started</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <p className="mb-4 text-xs font-medium uppercase tracking-widest text-primary">
          AI-powered study platform
        </p>
        <h1 className="text-5xl font-semibold tracking-tight text-foreground md:text-6xl">
          Turn your notes
          <br />
          into questions.
        </h1>
        <p className="mt-6 max-w-lg text-lg text-muted-foreground">
          Upload study material. AI generates multiple-choice questions. Practice
          with your class. Ship higher grades.
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Button size="lg" asChild>
            <Link to="/register">Get started free</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/login">Sign in</Link>
          </Button>
        </div>

        {/* How it works */}
        <Separator className="my-20 max-w-sm" />
        <div className="grid gap-8 text-left sm:grid-cols-3 sm:gap-12">
          {[
            { icon: Upload, title: "Upload", body: "Drop a PDF, DOCX, or scanned notes." },
            { icon: BrainCircuit, title: "AI drafts", body: "Questions are generated and ready for your review in seconds." },
            { icon: BookOpen, title: "Practice", body: "Published questions form a shared bank. Drill with your whole class." },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="space-y-3">
              <div className="inline-flex size-10 items-center justify-center rounded-[14px] bg-primary/10">
                <Icon className="size-5 text-primary" strokeWidth={1.5} />
              </div>
              <h3 className="font-medium text-foreground">{title}</h3>
              <p className="text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-border px-6 py-6 text-center text-xs text-muted-foreground">
        © 2026 StudentsClub. Full landing page coming in Phase 4.
      </footer>
    </div>
  );
}
