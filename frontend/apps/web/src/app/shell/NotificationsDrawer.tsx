import { Bell } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { EmptyState } from "@/components/design";

type NotificationsDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function NotificationsDrawer({
  open,
  onOpenChange,
}: NotificationsDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-sm p-0">
        <SheetHeader className="border-b border-border px-6 py-4">
          <SheetTitle className="text-base font-medium">
            Notifications
          </SheetTitle>
        </SheetHeader>
        <div className="flex h-full flex-col p-6">
          <EmptyState
            icon={Bell}
            title="All caught up"
            description="New notifications appear here — when a draft is ready for review, a question gets upvoted, or new material is posted in your subjects."
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}
