import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import {
  Bell,
  Check,
  Languages,
  Lock,
  Palette,
  Trash2,
  User as UserIcon,
} from "lucide-react";
import {
  getSettingsGetQueryKey,
  useSettingsGet,
  useSettingsUpdate,
} from "@/api/generated/endpoints/settings/settings";
import type {
  DensityPreference,
  ThemePreference,
  UserSettingsUpdate,
} from "@/api/generated/schemas";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/design/PageHeader";
import { cn } from "@/lib/utils";
import {
  ACCENT_PRESETS,
  COLOR_SCHEMES,
  isAccentId,
  type AccentId,
} from "@/lib/themes";
import { useAccent } from "@/lib/use-accent";

const NOTIFICATION_PREFS: { key: string; label: string; description: string }[] = [
  {
    key: "draft_ready",
    label: "Draft ready",
    description: "When AI finishes generating your uploaded material",
  },
  {
    key: "new_material_in_subject",
    label: "New material in your subjects",
    description: "When a classmate publishes a new question set",
  },
  {
    key: "question_set_voted",
    label: "Question feedback",
    description: "When your published questions get upvoted or flagged",
  },
];

const DENSITY_OPTIONS: { value: DensityPreference; label: string }[] = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
];

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "ar", label: "العربية (Arabic — preview)" },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const { accent, setAccent } = useAccent();

  const { data: settings, isLoading } = useSettingsGet({
    query: { enabled: !!user },
  });

  const updateMutation = useSettingsUpdate({
    mutation: {
      onSuccess: () => {
        toast.success("Settings updated");
        void queryClient.invalidateQueries({ queryKey: getSettingsGetQueryKey() });
      },
      onError: () => toast.error("Failed to save"),
    },
  });

  // Backend → local sync: when settings load, reconcile theme + accent so the UI
  // reflects the persisted choice across devices.
  useEffect(() => {
    if (!settings) return;
    if (settings.theme && settings.theme !== theme) {
      setTheme(settings.theme);
    }
    if (isAccentId(settings.accent_color) && settings.accent_color !== accent) {
      setAccent(settings.accent_color);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings?.theme, settings?.accent_color]);

  if (!user) {
    navigate("/login");
    return null;
  }

  function patch(data: UserSettingsUpdate) {
    updateMutation.mutate({ data });
  }

  function handleThemeChange(next: ThemePreference) {
    setTheme(next); // immediate visual swap, no flash
    patch({ theme: next });
  }

  function handleAccentChange(next: AccentId) {
    setAccent(next); // immediate visual swap
    patch({ accent_color: next });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        description="Account, preferences, notifications, and language."
      />

      {/* Account */}
      <SettingsSection icon={UserIcon} title="Account" description="Read-only profile information">
        <div className="grid gap-4 sm:grid-cols-2">
          <ReadOnlyField label="Full name" value={user.full_name} />
          <ReadOnlyField label="Email" value={user.email} />
          <ReadOnlyField label="College" value={user.college} />
          <ReadOnlyField label="Academic year" value={String(user.academic_year)} />
        </div>
      </SettingsSection>

      {/* Password */}
      <SettingsSection icon={Lock} title="Password" description="Change your sign-in password">
        <Button variant="outline" disabled>
          Change password (coming soon)
        </Button>
      </SettingsSection>

      {/* Appearance */}
      <SettingsSection
        icon={Palette}
        title="Appearance"
        description="Color scheme, accent, and density"
      >
        <div className="space-y-6">
          <div>
            <Label className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Color scheme
            </Label>
            <div className="flex flex-wrap gap-2">
              {COLOR_SCHEMES.map((opt) => (
                <ChipButton
                  key={opt.id}
                  selected={(theme ?? "system") === opt.id}
                  onClick={() => handleThemeChange(opt.id)}
                >
                  {opt.label}
                </ChipButton>
              ))}
            </div>
          </div>

          <div>
            <Label className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Accent
            </Label>
            <div className="flex flex-wrap gap-2">
              {ACCENT_PRESETS.map((opt) => {
                const selected = accent === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleAccentChange(opt.id)}
                    aria-label={`${opt.label} accent`}
                    aria-pressed={selected}
                    className={cn(
                      "group flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                      selected
                        ? "border-foreground/40 bg-muted text-foreground"
                        : "border-border bg-card text-muted-foreground hover:bg-muted/60",
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "flex size-4 shrink-0 items-center justify-center rounded-full ring-1 ring-border",
                      )}
                      style={{ backgroundColor: opt.preview }}
                    >
                      {selected && (
                        <Check className="size-2.5 text-white" strokeWidth={3} />
                      )}
                    </span>
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {isLoading || !settings ? (
            <Skeleton className="h-12 w-full" />
          ) : (
            <div>
              <Label className="mb-2 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Density
              </Label>
              <div className="flex flex-wrap gap-2">
                {DENSITY_OPTIONS.map((opt) => (
                  <ChipButton
                    key={opt.value}
                    selected={settings.density === opt.value}
                    onClick={() => patch({ density: opt.value })}
                  >
                    {opt.label}
                  </ChipButton>
                ))}
              </div>
            </div>
          )}
        </div>
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection icon={Bell} title="Notifications" description="Choose what you'd like to hear about">
        {isLoading || !settings ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <NotificationPrefsForm
            value={(settings.notification_prefs ?? {}) as Record<string, boolean>}
            onChange={(next) => patch({ notification_prefs: next })}
          />
        )}
      </SettingsSection>

      {/* Language */}
      <SettingsSection icon={Languages} title="Language" description="Interface language">
        {isLoading || !settings ? (
          <Skeleton className="h-12 w-64" />
        ) : (
          <select
            className="h-10 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/20"
            value={settings.language}
            onChange={(e) => patch({ language: e.target.value })}
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}
      </SettingsSection>

      {/* Danger zone */}
      <SettingsSection
        icon={Trash2}
        title="Danger zone"
        description="Sign out of this device or delete your account"
        tone="destructive"
      >
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={logout}>
            Sign out
          </Button>
          <Button variant="outline" disabled className="text-destructive">
            Delete account (coming soon)
          </Button>
        </div>
      </SettingsSection>
    </div>
  );
}

function SettingsSection({
  icon: Icon,
  title,
  description,
  tone = "default",
  children,
}: {
  icon: typeof UserIcon;
  title: string;
  description?: string;
  tone?: "default" | "destructive";
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-[14px] border border-border bg-card p-6",
        tone === "destructive" && "border-destructive/30",
      )}
    >
      <div className="mb-4 flex items-start gap-3">
        <div
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-lg",
            tone === "destructive" ? "bg-destructive/10" : "bg-primary/10",
          )}
        >
          <Icon
            className={cn(
              "size-4",
              tone === "destructive" ? "text-destructive" : "text-primary",
            )}
            strokeWidth={1.5}
          />
        </div>
        <div>
          <h2 className="text-base font-medium text-foreground">{title}</h2>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      <div>{children}</div>
    </section>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </Label>
      <Input value={value} readOnly className="bg-muted/40" />
    </div>
  );
}

function ChipButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-4 py-1.5 text-xs font-medium transition-colors",
        selected
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-muted text-muted-foreground hover:bg-muted/80",
      )}
    >
      {children}
    </button>
  );
}

function NotificationPrefsForm({
  value,
  onChange,
}: {
  value: Record<string, boolean>;
  onChange: (next: Record<string, boolean>) => void;
}) {
  const [local, setLocal] = useState(value);
  useEffect(() => setLocal(value), [value]);

  function toggle(key: string) {
    const next = { ...local, [key]: !(local[key] ?? true) };
    setLocal(next);
    onChange(next);
  }

  return (
    <ul className="divide-y divide-border">
      {NOTIFICATION_PREFS.map((p) => {
        const enabled = local[p.key] ?? true;
        return (
          <li key={p.key} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
            <div>
              <p className="text-sm font-medium text-foreground">{p.label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{p.description}</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={enabled}
              aria-label={`${p.label} notifications`}
              onClick={() => toggle(p.key)}
              className={cn(
                "relative h-6 w-11 shrink-0 rounded-full transition-colors",
                enabled ? "bg-primary" : "bg-muted-foreground/30",
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 size-5 rounded-full bg-white transition-transform",
                  enabled ? "translate-x-[1.375rem]" : "translate-x-0.5",
                )}
              />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

