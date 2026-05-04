import * as React from "react";
import { cn } from "@/lib/utils";

type ChipVariant =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "destructive"
  | "outline";

type ChipProps = React.ComponentProps<"span"> & {
  variant?: ChipVariant;
  size?: "sm" | "md";
};

const variantClasses: Record<ChipVariant, string> = {
  neutral: "bg-muted text-foreground",
  primary: "bg-primary/15 text-primary",
  success: "bg-[color:var(--success)]/15 text-[color:var(--success)]",
  warning: "bg-[color:var(--warning)]/15 text-[color:var(--warning)]",
  destructive: "bg-destructive/15 text-destructive",
  outline: "border border-border text-foreground",
};

/**
 * Chip — small inline label / status badge / filter pill. Use for difficulty
 * tags, status badges (Draft / Published / Rejected), filter selections.
 * Buttoned chips: pass `as="button"` semantically by wrapping or using the
 * native attribute pattern; this primitive renders <span> by default.
 */
export function Chip({
  className,
  variant = "neutral",
  size = "md",
  ...props
}: ChipProps) {
  return (
    <span
      data-slot="chip"
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium tracking-tight",
        size === "sm" && "px-2 py-0.5 text-[11px]",
        size === "md" && "px-2.5 py-1 text-xs",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
