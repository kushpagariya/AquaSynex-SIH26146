import { cn } from "@/lib/utils"
import type { AlertStatus, EntityType, Severity } from "@/data/types"

const severityStyles: Record<Severity, string> = {
  low: "text-risk-low bg-risk-low-soft border-risk-low/30",
  medium: "text-risk-medium bg-risk-medium-soft border-risk-medium/30",
  high: "text-risk-high bg-risk-high-soft border-risk-high/30",
  critical: "text-risk-critical bg-risk-critical-soft border-risk-critical/40",
}

const severityDot: Record<Severity, string> = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
}

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        severityStyles[severity],
        className,
      )}
    >
      <span className={cn("size-1.5 rounded-full", severityDot[severity])} />
      {severity}
    </span>
  )
}

export function severityColorVar(severity: Severity): string {
  return `var(--color-risk-${severity})`
}

/** Numeric risk score with a colored ring, sized sm | md | lg. */
export function RiskScore({
  score,
  severity,
  size = "md",
  className,
}: {
  score: number
  severity: Severity
  size?: "sm" | "md" | "lg"
  className?: string
}) {
  const dims =
    size === "lg"
      ? "size-24 text-3xl"
      : size === "sm"
        ? "size-10 text-sm"
        : "size-16 text-xl"

  const color = severityColorVar(severity)

  return (
    <div
      className={cn(
        "relative grid place-items-center rounded-full font-mono-id font-semibold tabular-nums",
        dims,
        className,
      )}
      style={{
        background: `conic-gradient(${color} ${score * 3.6}deg, var(--color-line) 0deg)`,
      }}
      role="img"
      aria-label={`Risk score ${score} of 100, ${severity}`}
    >
      <div className="absolute inset-[3px] grid place-items-center rounded-full bg-panel">
        <span style={{ color }}>{score}</span>
      </div>
    </div>
  )
}

const statusStyles: Record<AlertStatus, string> = {
  new: "text-accent bg-accent-soft border-accent/30",
  reviewing: "text-risk-medium bg-risk-medium-soft border-risk-medium/30",
  escalated: "text-risk-high bg-risk-high-soft border-risk-high/30",
  resolved: "text-risk-low bg-risk-low-soft border-risk-low/30",
  dismissed: "text-fg-subtle bg-panel-2 border-line",
}

export function StatusBadge({
  status,
  className,
}: {
  status: AlertStatus
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium capitalize",
        statusStyles[status],
        className,
      )}
    >
      {status}
    </span>
  )
}

const entityTypeLabel: Record<EntityType, string> = {
  wallet: "Wallet",
  transaction: "Transaction",
  ip: "IP",
  network: "Network",
  exchange: "Exchange",
  mixer: "Mixer",
}

export function EntityTypeBadge({
  type,
  className,
}: {
  type: EntityType
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border border-line bg-panel-2 px-2 py-0.5 text-[11px] font-medium text-fg-muted",
        className,
      )}
    >
      {entityTypeLabel[type]}
    </span>
  )
}
