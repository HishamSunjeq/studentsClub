import { NavLink, Navigate, Outlet } from "react-router";
import {
  Activity,
  BarChart3,
  KeyRound,
  Cpu,
  ScrollText,
  SlidersHorizontal,
} from "lucide-react";
import { useAuthStore } from "@/features/auth/auth.store";
import { PageHeader } from "@/components/design";
import { cn } from "@/lib/utils";

const ADMIN_NAV = [
  { label: "Dashboard", icon: BarChart3, to: "/admin" },
  { label: "AI runs", icon: Activity, to: "/admin/runs" },
  { label: "Credentials", icon: KeyRound, to: "/admin/credentials" },
  { label: "Models", icon: Cpu, to: "/admin/models" },
  { label: "Prompts", icon: ScrollText, to: "/admin/prompts" },
  { label: "Profiles", icon: SlidersHorizontal, to: "/admin/profiles" },
];

export default function AdminLayout() {
  const { user } = useAuthStore();

  if (user && user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        eyebrow="Control plane"
        title="AI administration"
        description="Manage provider credentials, models, prompts, generation profiles, and inspect telemetry — all without touching env files."
      />

      <nav className="flex flex-wrap gap-1 border-b border-border pb-px">
        {ADMIN_NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/admin"}
            className={({ isActive }) =>
              cn(
                "-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )
            }
          >
            <item.icon className="size-4" strokeWidth={1.5} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
