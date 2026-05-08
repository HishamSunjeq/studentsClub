import { useState } from "react";
import { Outlet, NavLink } from "react-router";
import {
  BookOpen,
  BrainCircuit,
  FileText,
  History,
  LayoutDashboard,
  Upload,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette, useCommandPalette } from "./CommandPalette";
import { NotificationsDrawer } from "./NotificationsDrawer";
import { useNotificationsList } from "@/api/generated/endpoints/notifications/notifications";
import { useAuthStore } from "@/features/auth/auth.store";

const MOBILE_NAV = [
  { label: "Home", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Subjects", icon: BookOpen, to: "/subjects" },
  { label: "Upload", icon: Upload, to: "/upload" },
  { label: "Drafts", icon: FileText, to: "/drafts" },
  { label: "Quiz", icon: BrainCircuit, to: "/quiz" },
];

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const { open: paletteOpen, setOpen: setPaletteOpen } = useCommandPalette();
  const accessToken = useAuthStore((s) => s.accessToken);

  // Unread count for the bell badge — refetched every 60s.
  const { data: notifData } = useNotificationsList(
    { size: 1, unread_only: true },
    {
      query: {
        enabled: !!accessToken,
        refetchInterval: 60_000,
        staleTime: 30_000,
      },
    },
  );
  const unreadCount = notifData?.unread_count ?? 0;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop sidebar — always visible ≥ md */}
      <div className="hidden shrink-0 md:flex">
        <Sidebar />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-50 flex md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileNavOpen(false)}
          />
          {/* Sidebar panel */}
          <div className="relative z-10 flex">
            <Sidebar onClose={() => setMobileNavOpen(false)} />
            <button
              className="absolute right-3 top-3 rounded-md p-1.5 text-muted-foreground hover:bg-muted"
              onClick={() => setMobileNavOpen(false)}
              aria-label="Close menu"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileNavOpen(true)}
          onSearchClick={() => setPaletteOpen(true)}
          onNotificationsClick={() => setNotificationsOpen(true)}
          notificationCount={unreadCount}
        />

        {/* Page content */}
        <main
          id="main-content"
          className="flex-1 overflow-y-auto"
          tabIndex={-1}
        >
          <div className="container-page py-8 pb-24 md:pb-8">
            <Outlet />
          </div>
        </main>

        {/* Mobile bottom tab bar */}
        <nav
          aria-label="Mobile navigation"
          className="flex shrink-0 border-t border-border bg-sidebar md:hidden"
        >
          {MOBILE_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      "size-5",
                      isActive ? "text-primary" : "text-muted-foreground",
                    )}
                    strokeWidth={1.5}
                  />
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
          <NavLink
            to="/history"
            className={({ isActive }) =>
              cn(
                "flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <History
                  className={cn(
                    "size-5",
                    isActive ? "text-primary" : "text-muted-foreground",
                  )}
                  strokeWidth={1.5}
                />
                History
              </>
            )}
          </NavLink>
        </nav>
      </div>

      {/* Portaled overlays */}
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <NotificationsDrawer
        open={notificationsOpen}
        onOpenChange={setNotificationsOpen}
      />
    </div>
  );
}
