import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * StudyCard — the canonical content container for the Premium Academic system.
 * Spec: bg surface-low, 1px border, 14px radius, 32px padding (generous to let
 * serif typography breathe). Use for question cards, dashboard widgets, lists.
 */
type StudyCardProps = React.ComponentProps<"div"> & {
  padding?: "default" | "compact" | "none";
  interactive?: boolean;
};

function StudyCard({
  className,
  padding = "default",
  interactive = false,
  ...props
}: StudyCardProps) {
  return (
    <div
      data-slot="study-card"
      className={cn(
        "rounded-[14px] border border-border bg-card text-card-foreground",
        padding === "default" && "p-8",
        padding === "compact" && "p-5",
        padding === "none" && "p-0",
        interactive &&
          "transition-colors duration-150 hover:border-ring/40 focus-within:border-ring",
        className,
      )}
      {...props}
    />
  );
}

function StudyCardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="study-card-header"
      className={cn("mb-4 flex items-start justify-between gap-4", className)}
      {...props}
    />
  );
}

function StudyCardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="study-card-title"
      className={cn(
        "font-sans text-lg font-medium tracking-tight text-foreground",
        className,
      )}
      {...props}
    />
  );
}

function StudyCardDescription({
  className,
  ...props
}: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="study-card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

function StudyCardContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="study-card-content"
      className={cn("text-sm text-foreground", className)}
      {...props}
    />
  );
}

function StudyCardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="study-card-footer"
      className={cn("mt-6 flex items-center gap-3", className)}
      {...props}
    />
  );
}

export {
  StudyCard,
  StudyCardHeader,
  StudyCardTitle,
  StudyCardDescription,
  StudyCardContent,
  StudyCardFooter,
};
