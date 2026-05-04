import { NavLink } from "react-router";
import {
  BookOpen,
  BrainCircuit,
  FileText,
  GraduationCap,
  HelpCircle,
  History,
  LayoutDashboard,
  Settings,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/features/auth/auth.store";
import { Button } from "@/components/ui/button";

const PRIMARY_NAV = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Subjects", icon: BookOpen, to: "/subjects" },
  { label: "Upload", icon: Upload, to: "/upload" },
  { label: "Drafts", icon: FileText, to: "/drafts" },
  { label: "Quiz", icon: BrainCircuit, to: "/quiz" },
  { label: "History", icon: History, to: "/history" },
];

const SECONDARY_NAV = [
  { label: "Settings", icon: Settings, to: "/settings" },
  { label: "Support", icon: HelpCircle, to: "/support" },
];

type SidebarProps = {
  onClose?: () => void;
};

export function Sidebar({ onClose }: SidebarProps) {
  const { user } = useAuthStore();

  return (
    <aside
      aria-label="Main navigation"
      className={cn(
        "flex h-full w-[var(--sidebar-width)] flex-col border-r border-border",
        "bg-sidebar py-6",
      )}
    >
      {/* Logo + user identity */}
      <div className="mb-8 flex items-center gap-3 px-6">
        <div className="flex size-10 items-center justify-center rounded-full bg-primary/15">
          <GraduationCap className="size-5 text-primary" strokeWidth={1.5} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-base font-semibold tracking-tight text-sidebar-foreground">
            StudentsClub
          </p>
          {user ? (
            <p className="truncate text-xs text-muted-foreground">
              {user.full_name}
            </p>
          ) : null}
        </div>
      </div>

      {/* Primary nav */}
      <nav className="flex-1 px-3" onClick={onClose}>
        <ul className="space-y-0.5">
          {PRIMARY_NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-primary"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon
                      className={cn(
                        "size-5 shrink-0",
                        isActive ? "text-primary" : "text-muted-foreground",
                      )}
                      strokeWidth={1.5}
                    />
                    {item.label}
                    {isActive && (
                      <span
                        aria-hidden
                        className="ml-auto h-4 w-0.5 rounded-full bg-primary"
                      />
                    )}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Secondary nav + CTA */}
      <div className="mt-auto border-t border-border px-3 pt-4">
        <ul className="space-y-0.5" onClick={onClose}>
          {SECONDARY_NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-primary"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon
                      className={cn(
                        "size-5 shrink-0",
                        isActive ? "text-primary" : "text-muted-foreground",
                      )}
                      strokeWidth={1.5}
                    />
                    {item.label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
        <Button
          className="mt-4 w-full"
          size="sm"
          onClick={() => {
            onClose?.();
          }}
          asChild
        >
          <NavLink to="/upload">
            <Upload className="size-3.5" strokeWidth={1.5} />
            Upload Material
          </NavLink>
        </Button>
      </div>
    </aside>
  );
}
