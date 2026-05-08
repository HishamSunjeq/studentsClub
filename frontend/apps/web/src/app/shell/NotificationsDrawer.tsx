import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { Bell, BookOpen, FileText, Sparkles } from "lucide-react";
import {
  getNotificationsListQueryKey,
  notificationsMarkAllRead,
  notificationsMarkRead,
  useNotificationsList,
} from "@/api/generated/endpoints/notifications/notifications";
import type {
  NotificationResponse,
  NotificationType,
} from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/design";
import { useAuthStore } from "@/features/auth/auth.store";
import { cn } from "@/lib/utils";

type NotificationsDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const TYPE_ICON: Record<NotificationType, typeof Bell> = {
  draft_ready: Sparkles,
  question_set_published: FileText,
  question_set_voted: BookOpen,
  new_material_in_subject: BookOpen,
};

export function NotificationsDrawer({
  open,
  onOpenChange,
}: NotificationsDrawerProps) {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const { data, isLoading } = useNotificationsList(
    { size: 30 },
    { query: { enabled: !!user && open } },
  );

  const items = data?.items ?? [];
  const unreadCount = data?.unread_count ?? 0;

  function invalidate() {
    void queryClient.invalidateQueries({
      queryKey: getNotificationsListQueryKey(),
    });
  }

  async function handleClick(n: NotificationResponse) {
    if (!n.read_at) {
      try {
        await notificationsMarkRead(n.id);
        invalidate();
      } catch {
        // Best-effort
      }
    }
    onOpenChange(false);
    // Navigate based on payload
    const payload = (n.payload ?? {}) as {
      subject_id?: string;
      question_set_id?: string;
    };
    if (payload.question_set_id && payload.subject_id) {
      navigate(`/subjects/${payload.subject_id}`);
    } else if (payload.subject_id) {
      navigate(`/subjects/${payload.subject_id}`);
    }
  }

  async function handleMarkAllRead() {
    try {
      await notificationsMarkAllRead();
      invalidate();
    } catch {
      // best-effort
    }
  }

  // Group by day
  const groups = groupByDay(items);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-sm p-0">
        <SheetHeader className="border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-base font-medium">
              Notifications
              {unreadCount > 0 && (
                <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                  {unreadCount}
                </span>
              )}
            </SheetTitle>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-primary hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>
        </SheetHeader>

        <div className="h-full overflow-y-auto p-4">
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-lg" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="flex h-full items-center justify-center pt-10">
              <EmptyState
                icon={Bell}
                title="All caught up"
                description="When a draft is ready or new material is posted in your subjects, it'll appear here."
              />
            </div>
          ) : (
            <div className="space-y-6">
              {groups.map(([label, group]) => (
                <div key={label}>
                  <p className="mb-2 px-1 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    {label}
                  </p>
                  <ul className="space-y-1">
                    {group.map((n) => {
                      const Icon = TYPE_ICON[n.type] ?? Bell;
                      const unread = !n.read_at;
                      return (
                        <li key={n.id}>
                          <button
                            onClick={() => handleClick(n)}
                            className={cn(
                              "group flex w-full items-start gap-3 rounded-lg p-3 text-left transition-colors hover:bg-muted/50",
                              unread && "bg-primary/5",
                            )}
                          >
                            <div className="relative">
                              <div className="flex size-8 items-center justify-center rounded-lg bg-muted">
                                <Icon
                                  className="size-4 text-muted-foreground"
                                  strokeWidth={1.5}
                                />
                              </div>
                              {unread && (
                                <span
                                  aria-hidden
                                  className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-primary"
                                />
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p
                                className={cn(
                                  "text-xs",
                                  unread
                                    ? "font-medium text-foreground"
                                    : "text-muted-foreground",
                                )}
                              >
                                {n.title}
                              </p>
                              {n.body && (
                                <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                                  {n.body}
                                </p>
                              )}
                              <p className="mt-1 text-[10px] text-muted-foreground/70">
                                {timeAgo(new Date(n.created_at))}
                              </p>
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>

        {items.length > 0 && (
          <div className="border-t border-border p-3">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={() => {
                onOpenChange(false);
              }}
            >
              Close
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function groupByDay(items: NotificationResponse[]): [string, NotificationResponse[]][] {
  const groups: Record<string, NotificationResponse[]> = {};
  const order: string[] = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  for (const n of items) {
    const d = new Date(n.created_at);
    d.setHours(0, 0, 0, 0);
    let label: string;
    if (d.getTime() === today.getTime()) label = "Today";
    else if (d.getTime() === yesterday.getTime()) label = "Yesterday";
    else label = d.toLocaleDateString();
    if (!(label in groups)) {
      groups[label] = [];
      order.push(label);
    }
    groups[label].push(n);
  }
  return order.map((l) => [l, groups[l]]);
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
