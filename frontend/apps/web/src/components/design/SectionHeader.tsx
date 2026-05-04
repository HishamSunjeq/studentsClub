import * as React from "react";
import { cn } from "@/lib/utils";

type SectionHeaderProps = React.ComponentProps<"div"> & {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
};

/**
 * SectionHeader — header for a sub-section within a page (e.g. each bento tile,
 * subject-detail tabs). Smaller than PageHeader, but consistent typography.
 */
export function SectionHeader({
  className,
  title,
  description,
  action,
  ...props
}: SectionHeaderProps) {
  return (
    <div
      data-slot="section-header"
      className={cn(
        "flex items-end justify-between gap-4 pb-4",
        className,
      )}
      {...props}
    >
      <div className="space-y-1">
        <h2 className="text-lg font-medium tracking-tight text-foreground">
          {title}
        </h2>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
