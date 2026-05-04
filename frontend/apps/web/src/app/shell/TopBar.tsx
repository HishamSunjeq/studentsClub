import { Bell, Menu, Search } from "lucide-react";
import { NavLink } from "react-router";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/features/auth/auth.store";
import { GraduationCap, LogOut, Settings, User } from "lucide-react";

type TopBarProps = {
  onMenuClick: () => void;
  onSearchClick: () => void;
  onNotificationsClick: () => void;
  notificationCount?: number;
};

export function TopBar({
  onMenuClick,
  onSearchClick,
  onNotificationsClick,
  notificationCount = 0,
}: TopBarProps) {
  const { user, logout } = useAuthStore();

  const initials = user?.full_name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center border-b border-border bg-background/80 backdrop-blur-md">
      <div className="flex w-full items-center gap-3 px-4">
        {/* Mobile: hamburger + logo */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <Menu className="size-5" strokeWidth={1.5} />
        </Button>
        <NavLink
          to="/dashboard"
          className="mr-2 flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground md:hidden"
        >
          <GraduationCap className="size-4 text-primary" strokeWidth={1.5} />
          StudentsClub
        </NavLink>

        {/* Desktop: search trigger */}
        <button
          onClick={onSearchClick}
          className="hidden h-9 w-64 items-center gap-3 rounded-lg border border-border bg-muted/50 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted md:flex"
          aria-label="Open search"
        >
          <Search className="size-4 shrink-0" strokeWidth={1.5} />
          <span className="flex-1 text-left">Search…</span>
          <kbd className="hidden rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:block">
            ⌘K
          </kbd>
        </button>

        <div className="ml-auto flex items-center gap-1">
          {/* Mobile search */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={onSearchClick}
            aria-label="Search"
          >
            <Search className="size-5" strokeWidth={1.5} />
          </Button>

          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onNotificationsClick}
            aria-label={
              notificationCount
                ? `${notificationCount} notifications`
                : "Notifications"
            }
            className="relative"
          >
            <Bell className="size-5" strokeWidth={1.5} />
            {notificationCount > 0 && (
              <span
                aria-hidden
                className="absolute right-1.5 top-1.5 flex size-2 rounded-full bg-primary"
              />
            )}
          </Button>

          {/* Avatar dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Account menu"
                className="rounded-full"
              >
                <span className="flex size-7 items-center justify-center rounded-full bg-primary/20 text-xs font-semibold text-primary">
                  {initials ?? <User className="size-4" strokeWidth={1.5} />}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              {user && (
                <>
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-0.5">
                      <span className="text-sm font-medium">
                        {user.full_name}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {user.email}
                      </span>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem asChild>
                <NavLink to="/profile">
                  <User className="size-4" strokeWidth={1.5} />
                  Profile
                </NavLink>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <NavLink to="/settings">
                  <Settings className="size-4" strokeWidth={1.5} />
                  Settings
                </NavLink>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={logout}
              >
                <LogOut className="size-4" strokeWidth={1.5} />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
