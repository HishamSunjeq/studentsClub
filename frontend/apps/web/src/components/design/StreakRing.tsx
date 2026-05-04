import * as React from "react";
import { cn } from "@/lib/utils";

type StreakRingProps = {
  /** Current value (0..max). */
  value: number;
  /** Maximum value the ring represents. Default 7 (weekly streak). */
  max?: number;
  /** Total ring diameter in px. */
  size?: number;
  /** Stroke width — kept hairline per spec. */
  stroke?: number;
  /** Caption below the value. */
  label?: React.ReactNode;
  /** Suffix shown after the numeric value (e.g. "days"). */
  suffix?: React.ReactNode;
  className?: string;
};

/**
 * StreakRing — minimal hairline-stroke circular progress per Premium Academic
 * "Focus Timer" spec. Used for streak, weekly-goal, quiz timer.
 */
export function StreakRing({
  value,
  max = 7,
  size = 120,
  stroke = 4,
  label,
  suffix,
  className,
}: StreakRingProps) {
  const safeMax = Math.max(1, max);
  const safeValue = Math.max(0, Math.min(value, safeMax));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - safeValue / safeMax);

  return (
    <div
      data-slot="streak-ring"
      className={cn(
        "relative inline-flex items-center justify-center",
        className,
      )}
      style={{ width: size, height: size }}
      role="img"
      aria-label={
        typeof label === "string"
          ? `${label}: ${safeValue} of ${safeMax}`
          : `${safeValue} of ${safeMax}`
      }
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          className="text-border"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="text-primary transition-[stroke-dashoffset] duration-500 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tracking-tight text-foreground">
          {safeValue}
          {suffix ? (
            <span className="ml-0.5 text-sm font-medium text-muted-foreground">
              {suffix}
            </span>
          ) : null}
        </span>
        {label ? (
          <span className="mt-0.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
