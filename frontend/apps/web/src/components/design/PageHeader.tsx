import * as React from "react";
import { cn } from "@/lib/utils";

type PageHeaderProps = React.ComponentProps<"header"> & {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
};

/**
 * PageHeader — the standard page intro block. Use at the top of every full page
 * (Dashboard, Subjects, Drafts, Profile, Settings, ...).
 */
export function PageHeader({
  className,
  eyebrow,
  title,
  description,
  actions,
  ...props
}: PageHeaderProps) {
  return (
    <header
      data-slot="page-header"
      className={cn(
        "flex flex-col gap-4 pb-8 md:flex-row md:items-end md:justify-between",
        className,
      )}
      {...props}
    >
      <div className="space-y-2">
        {eyebrow ? (
          <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {eyebrow}
          </div>
        ) : null}
        <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
          {title}
        </h1>
        {description ? (
          <p className="max-w-prose text-base text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex items-center gap-2 md:shrink-0">{actions}</div>
      ) : null}
    </header>
  );
}
