import * as React from "react";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type Trend = {
  value: string;
  direction: "up" | "down" | "flat";
};

type StatTileProps = React.ComponentProps<"div"> & {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: LucideIcon;
  trend?: Trend;
  accent?: "primary" | "success" | "warning" | "destructive";
};

const accentClasses: Record<NonNullable<StatTileProps["accent"]>, string> = {
  primary: "text-primary",
  success: "text-[color:var(--success)]",
  warning: "text-[color:var(--warning)]",
  destructive: "text-destructive",
};

const trendClasses: Record<Trend["direction"], string> = {
  up: "text-[color:var(--success)] bg-[color:var(--success)]/10",
  down: "text-destructive bg-destructive/10",
  flat: "text-muted-foreground bg-muted",
};

/**
 * StatTile — compact KPI display used on dashboard, profile stats, subject pages.
 * Tonal-layer styling per spec — no shadow, just border + slight bg lift.
 */
export function StatTile({
  className,
  label,
  value,
  hint,
  icon: Icon,
  trend,
  accent = "primary",
  ...props
}: StatTileProps) {
  return (
    <div
      data-slot="stat-tile"
      className={cn(
        "rounded-[14px] border border-border bg-card p-6",
        className,
      )}
      {...props}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {label}
        </span>
        {Icon ? (
          <Icon
            aria-hidden
            className={cn("size-5", accentClasses[accent])}
            strokeWidth={1.5}
          />
        ) : null}
      </div>
      <div className="mt-3 flex items-baseline gap-3">
        <span className="text-3xl font-semibold tracking-tight text-foreground">
          {value}
        </span>
        {trend ? (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium",
              trendClasses[trend.direction],
            )}
          >
            {trend.direction === "up" ? (
              <ArrowUpRight className="size-3" strokeWidth={2} />
            ) : trend.direction === "down" ? (
              <ArrowDownRight className="size-3" strokeWidth={2} />
            ) : null}
            {trend.value}
          </span>
        ) : null}
      </div>
      {hint ? (
        <div className="mt-2 text-xs text-muted-foreground">{hint}</div>
      ) : null}
    </div>
  );
}
