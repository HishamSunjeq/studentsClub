import { useEffect, useState } from "react";
import {
  BookOpen,
  Flame,
  GraduationCap,
  Inbox,
  Sparkles,
  Sun,
  Moon,
  Trophy,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Chip,
  DonutChart,
  EmptyState,
  PageHeader,
  SectionHeader,
  StatTile,
  StreakRing,
  StudyCard,
  StudyCardContent,
  StudyCardDescription,
  StudyCardFooter,
  StudyCardHeader,
  StudyCardTitle,
} from "@/components/design";

/**
 * /dev/components — visual QA for the Premium Academic design system.
 * Renders every primitive in both themes. Excluded from production builds
 * via the route guard in src/App.tsx.
 */
export default function ComponentsShowcasePage() {
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.classList.toggle("light", theme === "light");
  }, [theme]);

  return (
    <main className="min-h-screen bg-background">
      <div className="container-page py-12">
        <PageHeader
          eyebrow="Internal · Phase 1"
          title="Premium Academic — design system"
          description="Visual QA harness for tokens, typography, and design primitives. Toggle theme to verify both modes."
          actions={
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? (
                <Sun className="size-4" strokeWidth={1.5} />
              ) : (
                <Moon className="size-4" strokeWidth={1.5} />
              )}
              {theme === "dark" ? "Light" : "Dark"} mode
            </Button>
          }
        />

        <section className="space-y-6">
          <SectionHeader
            title="Typography"
            description="Inter for UI · Newsreader for study content."
          />
          <StudyCard className="space-y-4">
            <h1 className="text-5xl font-semibold tracking-tight text-foreground">
              Display XL — 48/600
            </h1>
            <h2 className="text-3xl font-semibold tracking-tight text-foreground">
              H1 — 32/600
            </h2>
            <h3 className="text-2xl font-medium tracking-tight text-foreground">
              H2 — 24/500
            </h3>
            <p className="text-sm font-medium text-muted-foreground">
              UI medium — 14/500. Used for buttons, nav, metadata.
            </p>
            <Separator />
            <p className="font-study">
              Study body (Newsreader 18/1.6). Reserved for question stems,
              textbook excerpts, and AI-generated explanations. The serif and
              generous line height help the reader switch from "operating" to
              "absorbing." Lorem ipsum dolor sit amet, consectetur adipiscing
              elit. Sed do eiusmod tempor incididunt ut labore et dolore magna.
            </p>
            <p className="font-study-quote text-foreground">
              "Study quote (Newsreader 20/1.5) — used for highlighted excerpts."
            </p>
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Color tokens" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            <Swatch name="background" cls="bg-background" />
            <Swatch name="card" cls="bg-card" />
            <Swatch name="muted" cls="bg-muted" />
            <Swatch name="primary" cls="bg-primary" />
            <Swatch name="secondary" cls="bg-secondary" />
            <Swatch name="accent" cls="bg-accent" />
            <Swatch name="success" cls="bg-[color:var(--success)]" />
            <Swatch name="warning" cls="bg-[color:var(--warning)]" />
            <Swatch name="destructive" cls="bg-destructive" />
            <Swatch name="border" cls="bg-border" />
            <Swatch name="ring" cls="bg-ring" />
            <Swatch name="sidebar" cls="bg-sidebar" />
          </div>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader
            title="Buttons"
            description="shadcn primitives re-themed against Premium Academic tokens."
          />
          <StudyCard padding="compact" className="flex flex-wrap gap-3">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="link">Link</Button>
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Form controls" />
          <StudyCard padding="compact" className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="demo-email">Email</Label>
              <Input
                id="demo-email"
                type="email"
                placeholder="ada@university.edu"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="demo-disabled">Disabled</Label>
              <Input id="demo-disabled" disabled value="cannot edit me" />
            </div>
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Chips & badges" />
          <StudyCard padding="compact" className="flex flex-wrap gap-2">
            <Chip>Neutral</Chip>
            <Chip variant="primary">Primary</Chip>
            <Chip variant="success">Published</Chip>
            <Chip variant="warning">Needs edits</Chip>
            <Chip variant="destructive">Rejected</Chip>
            <Chip variant="outline">Outline</Chip>
            <Badge>shadcn badge</Badge>
            <Badge variant="secondary">secondary</Badge>
            <Badge variant="destructive">destructive</Badge>
            <Badge variant="outline">outline</Badge>
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader
            title="Stat tiles"
            description="Used on dashboard, profile, subject detail."
          />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label="Streak"
              value="5"
              hint="days in a row"
              icon={Flame}
              accent="warning"
              trend={{ value: "+1", direction: "up" }}
            />
            <StatTile
              label="XP earned"
              value="2,450"
              hint="this week"
              icon={Sparkles}
              accent="primary"
              trend={{ value: "+12%", direction: "up" }}
            />
            <StatTile
              label="Accuracy"
              value="87%"
              hint="last 30 days"
              icon={Trophy}
              accent="success"
            />
            <StatTile
              label="Drafts pending"
              value="3"
              hint="awaiting review"
              icon={Inbox}
              accent="primary"
              trend={{ value: "−2", direction: "down" }}
            />
          </div>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader
            title="Rings & charts"
            description="Hairline-stroke primitives matching the Focus Timer spec."
          />
          <div className="grid gap-6 md:grid-cols-3">
            <StudyCard className="flex items-center justify-center">
              <StreakRing
                value={5}
                max={7}
                label="Weekly goal"
                suffix="/7"
              />
            </StudyCard>
            <StudyCard className="flex items-center justify-center">
              <StreakRing
                value={42}
                max={60}
                size={140}
                label="Quiz timer"
                suffix="s"
              />
            </StudyCard>
            <StudyCard className="flex items-center justify-center">
              <DonutChart
                segments={[
                  { label: "Correct", value: 17 },
                  { label: "Incorrect", value: 2 },
                  { label: "Skipped", value: 1 },
                ]}
                centerLabel="85%"
                centerSubLabel="Score"
              />
            </StudyCard>
          </div>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Tabs" />
          <StudyCard padding="compact">
            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="members">Members</TabsTrigger>
                <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
              </TabsList>
              <TabsContent value="overview" className="pt-4 text-sm">
                Subject overview content goes here.
              </TabsContent>
              <TabsContent value="members" className="pt-4 text-sm">
                Members list goes here.
              </TabsContent>
              <TabsContent value="leaderboard" className="pt-4 text-sm">
                Leaderboard goes here.
              </TabsContent>
            </Tabs>
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Skeletons" />
          <StudyCard className="space-y-3">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-32 w-full" />
          </StudyCard>
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader
            title="Empty state"
            description="Standard pattern for any list/grid with no data."
          />
          <EmptyState
            icon={Upload}
            title="No uploads yet"
            description="Drop a PDF or DOCX of your study notes to generate your first question set."
            action={<Button>Upload material</Button>}
          />
        </section>

        <Separator className="my-12" />

        <section className="space-y-6">
          <SectionHeader title="Study card composition" />
          <div className="grid gap-4 md:grid-cols-2">
            <StudyCard interactive>
              <StudyCardHeader>
                <div className="space-y-1">
                  <StudyCardTitle>CS 101 — Algorithms</StudyCardTitle>
                  <StudyCardDescription>
                    Stanford · Year 2 · 1.2k members
                  </StudyCardDescription>
                </div>
                <Chip variant="success" size="sm">
                  Enrolled
                </Chip>
              </StudyCardHeader>
              <StudyCardContent className="font-study">
                Study the foundations of algorithmic thinking with sorting,
                searching, graph traversal, and dynamic programming.
              </StudyCardContent>
              <StudyCardFooter>
                <Button size="sm">
                  <BookOpen className="size-3.5" strokeWidth={1.5} />
                  Start quiz
                </Button>
                <Button size="sm" variant="ghost">
                  View
                </Button>
              </StudyCardFooter>
            </StudyCard>

            <StudyCard interactive>
              <StudyCardHeader>
                <div className="space-y-1">
                  <StudyCardTitle>BIO 220 — Genetics</StudyCardTitle>
                  <StudyCardDescription>
                    MIT · Year 3 · 840 members
                  </StudyCardDescription>
                </div>
                <Chip size="sm">Not enrolled</Chip>
              </StudyCardHeader>
              <StudyCardContent className="font-study">
                Mendelian inheritance, molecular genetics, and modern genomics.
                45 question sets contributed by 18 students.
              </StudyCardContent>
              <StudyCardFooter>
                <Button size="sm" variant="outline">
                  <GraduationCap className="size-3.5" strokeWidth={1.5} />
                  Enrol
                </Button>
              </StudyCardFooter>
            </StudyCard>
          </div>
        </section>

        <div className="mt-16 text-center text-xs text-muted-foreground">
          End of Phase 1 component showcase. Phase 2 builds the app shell.
        </div>
      </div>
    </main>
  );
}

function Swatch({ name, cls }: { name: string; cls: string }) {
  return (
    <div className="overflow-hidden rounded-[10px] border border-border">
      <div className={`${cls} h-12 w-full`} aria-hidden />
      <div className="bg-card px-2 py-1.5">
        <code className="text-[11px] text-muted-foreground">{name}</code>
      </div>
    </div>
  );
}
