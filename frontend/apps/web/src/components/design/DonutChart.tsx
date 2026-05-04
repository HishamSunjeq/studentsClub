import * as React from "react";
import { cn } from "@/lib/utils";

type DonutSegment = {
  label: string;
  value: number;
  /** A CSS color (var or hex). Defaults rotate through chart-1..chart-5. */
  color?: string;
};

type DonutChartProps = {
  segments: DonutSegment[];
  size?: number;
  stroke?: number;
  centerLabel?: React.ReactNode;
  centerSubLabel?: React.ReactNode;
  className?: string;
};

const DEFAULT_PALETTE = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

/**
 * DonutChart — minimal SVG donut for quiz result breakdowns and similar.
 * Pure SVG, no chart lib dependency. Hairline track behind segments matches
 * the StreakRing aesthetic.
 */
export function DonutChart({
  segments,
  size = 180,
  stroke = 16,
  centerLabel,
  centerSubLabel,
  className,
}: DonutChartProps) {
  const total = segments.reduce((sum, s) => sum + Math.max(0, s.value), 0) || 1;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulative = 0;
  const slices = segments.map((segment, idx) => {
    const value = Math.max(0, segment.value);
    const fraction = value / total;
    const dashLength = fraction * circumference;
    const offset = -cumulative;
    cumulative += dashLength;
    return {
      ...segment,
      color: segment.color ?? DEFAULT_PALETTE[idx % DEFAULT_PALETTE.length],
      dashLength,
      offset,
      key: `${segment.label}-${idx}`,
    };
  });

  return (
    <div
      data-slot="donut-chart"
      className={cn("inline-flex flex-col items-center gap-4", className)}
    >
      <div
        className="relative inline-flex items-center justify-center"
        style={{ width: size, height: size }}
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
          {slices.map((slice) => (
            <circle
              key={slice.key}
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={slice.color}
              strokeWidth={stroke}
              strokeDasharray={`${slice.dashLength} ${circumference}`}
              strokeDashoffset={slice.offset}
              strokeLinecap="butt"
            />
          ))}
        </svg>
        {(centerLabel || centerSubLabel) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            {centerLabel ? (
              <span className="text-2xl font-semibold tracking-tight text-foreground">
                {centerLabel}
              </span>
            ) : null}
            {centerSubLabel ? (
              <span className="mt-0.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                {centerSubLabel}
              </span>
            ) : null}
          </div>
        )}
      </div>
      {slices.length > 0 && (
        <ul className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {slices.map((slice) => (
            <li key={slice.key} className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="size-2.5 rounded-full"
                style={{ background: slice.color }}
              />
              <span className="text-foreground">{slice.label}</span>
              <span className="tabular-nums">{slice.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
