import { Flame, Inbox, Sparkles, Trophy } from "lucide-react";
import { PageHeader } from "@/components/design/PageHeader";
import { StatTile } from "@/components/design/StatTile";
import { useAuthStore } from "@/features/auth/auth.store";

// Stub — full bento-grid dashboard built in Phase 8.
export default function DashboardPage() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title={user ? `Welcome back, ${user.full_name.split(" ")[0]}` : "Dashboard"}
        description="Your study progress at a glance."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Streak"
          value="—"
          hint="coming in Phase 8"
          icon={Flame}
          accent="warning"
        />
        <StatTile
          label="XP earned"
          value="—"
          hint="coming in Phase 8"
          icon={Sparkles}
          accent="primary"
        />
        <StatTile
          label="Accuracy"
          value="—"
          hint="coming in Phase 8"
          icon={Trophy}
          accent="success"
        />
        <StatTile
          label="Drafts pending"
          value="—"
          hint="coming in Phase 8"
          icon={Inbox}
          accent="primary"
        />
      </div>

      <p className="text-sm text-muted-foreground">
        Full dashboard with bento grid, activity feed, and streak widgets will be
        built in Phase 8 once the backend stats endpoint is ready.
      </p>
    </div>
  );
}
