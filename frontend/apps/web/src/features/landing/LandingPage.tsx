import { Link } from "react-router";
import { BookMarked, Sparkles, Upload, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4 sm:px-10">
        <div className="flex items-center gap-3">
          <BookMarked className="size-5 text-primary" strokeWidth={1.5} />
          <span className="text-lg font-bold tracking-tight">StudentsClub</span>
        </div>
        <nav className="hidden items-center gap-8 sm:flex">
          <a
            href="#how-it-works"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            How it works
          </a>
        </nav>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login">Log in</Link>
          </Button>
          <Button size="sm" asChild>
            <Link to="/register">Get started</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex min-h-[480px] flex-col items-center justify-center gap-6 bg-gradient-to-b from-primary/8 to-background px-4 py-20 text-center">
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-black leading-tight tracking-tight text-foreground sm:text-5xl">
            Turn your notes into questions.
            <br />
            Practice with your class.
          </h1>
          <p className="text-base text-muted-foreground sm:text-lg">
            AI-powered collaborative learning for students.
          </p>
        </div>
        <Button size="lg" asChild>
          <Link to="/register">Get started free</Link>
        </Button>
      </section>

      {/* Live counter */}
      <section className="px-4 py-4 sm:px-10">
        <div className="mx-auto max-w-4xl">
          <div className="flex min-w-[160px] max-w-xs flex-col gap-2 rounded-lg border border-border p-6">
            <p className="text-base font-medium">Questions generated this week</p>
            <p className="text-2xl font-bold tracking-tight">12,840</p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="px-4 py-12 sm:px-10">
        <div className="mx-auto max-w-4xl flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              How it works
            </h2>
            <p className="text-base text-muted-foreground">
              Three simple steps to transform your study routine.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {([
              {
                Icon: Upload,
                title: "Upload notes",
                body: "Upload your lecture notes or slides in any format.",
              },
              {
                Icon: Sparkles,
                title: "AI generates drafts",
                body: "Our AI creates practice questions from your material.",
              },
              {
                Icon: Users,
                title: "Practice together",
                body: "Study and practice with your classmates.",
              },
            ] as const).map(({ Icon, title, body }) => (
              <div
                key={title}
                className="flex flex-col gap-3 rounded-lg border border-border bg-surface-low p-4"
              >
                <Icon className="size-6 text-foreground" strokeWidth={1.5} />
                <div className="flex flex-col gap-1">
                  <h3 className="text-base font-bold">{title}</h3>
                  <p className="text-sm text-muted-foreground">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="px-4 py-6 sm:px-10">
        <p className="text-center text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Trusted by students from
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-10 opacity-50 grayscale">
          {["Stanford", "MIT", "Harvard", "Oxford"].map((uni) => (
            <span key={uni} className="text-xl font-semibold uppercase tracking-widest text-muted-foreground">
              {uni}
            </span>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-16 border-t border-border bg-surface-low px-6 py-12 sm:px-10">
        <div className="mx-auto max-w-4xl flex flex-col gap-8 md:flex-row md:justify-between">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <BookMarked className="size-5 text-primary" strokeWidth={1.5} />
              <span className="text-xl font-semibold">StudentsClub</span>
            </div>
            <p className="max-w-xs text-sm text-muted-foreground">
              The premium AI-powered study platform designed for serious learners.
            </p>
          </div>
          <div className="flex gap-16 text-sm">
            <div className="flex flex-col gap-3">
              <span className="font-bold">Product</span>
              <a
                href="#how-it-works"
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                How it works
              </a>
            </div>
            <div className="flex flex-col gap-3">
              <span className="font-bold">Legal</span>
              <a href="#" className="text-muted-foreground transition-colors hover:text-primary">
                Privacy
              </a>
              <a href="#" className="text-muted-foreground transition-colors hover:text-primary">
                Terms
              </a>
            </div>
          </div>
        </div>
        <div className="mx-auto mt-12 max-w-4xl border-t border-border pt-8">
          <p className="text-xs text-muted-foreground">
            © 2026 StudentsClub. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
