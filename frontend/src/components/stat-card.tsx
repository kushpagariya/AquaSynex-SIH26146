import type { ComponentType } from "react"
import { ArrowDownRight, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatNumber } from "@/lib/utils"

export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  accent = "default",
  onClick,
}: {
  label: string
  value: number | string
  delta?: number
  icon: ComponentType<{ className?: string }>
  accent?: "default" | "critical" | "high" | "accent"
  onClick?: () => void
}) {
  const accentColor =
    accent === "critical"
      ? "text-risk-critical"
      : accent === "high"
        ? "text-risk-high"
        : accent === "accent"
          ? "text-accent"
          : "text-fg-muted"

  const up = (delta ?? 0) >= 0

  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-[var(--radius-panel)] border border-line bg-panel p-4 transition-colors",
        onClick && "cursor-pointer hover:bg-panel-2 hover:border-line-soft",
      )}
    >
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-fg-subtle">
          {label}
        </span>
        <Icon className={cn("size-4", accentColor)} />
      </div>
      <p className="mt-3 font-mono-id text-2xl font-semibold tabular-nums text-fg">
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      {delta !== undefined ? (
        <div
          className={cn(
            "mt-1 flex items-center gap-1 text-xs",
            up ? "text-risk-low" : "text-risk-critical",
          )}
        >
          {up ? (
            <ArrowUpRight className="size-3.5" />
          ) : (
            <ArrowDownRight className="size-3.5" />
          )}
          <span className="tabular-nums">{Math.abs(delta)}%</span>
          <span className="text-fg-subtle">vs. baseline</span>
        </div>
      ) : null}
    </div>
  )
}
