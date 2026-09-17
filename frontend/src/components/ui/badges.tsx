import { cn } from "@/lib/utils"
import type { AlertStatus, EntityType, Severity } from "@/data/types"

const severityStyles: Record<Severity, string> = {
  low: "text-[#2F6B4F] bg-[#EAF3EE] border-[#C5DECF]",
  medium: "text-[#A46A16] bg-[#FDF6E2] border-[#F2DF99]",
  high: "text-[#B85D1B] bg-[#FDF0E6] border-[#F6CCA9]",
  critical: "text-[#A63D3D] bg-[#FDF0F0] border-[#F4BCBC]",
}

const severityDot: Record<Severity, string> = {
  low: "bg-[#2F6B4F]",
  medium: "bg-[#A46A16]",
  high: "bg-[#B85D1B]",
  critical: "bg-[#A63D3D]",
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
        "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
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
  switch (severity) {
    case "low":
      return "#2F6B4F"
    case "medium":
      return "#A46A16"
    case "high":
      return "#B85D1B"
    case "critical":
      return "#A63D3D"
    default:
      return "#666666"
  }
}

/** Numeric risk score with restrained institutional indicator */
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
      ? "size-20 text-2xl"
      : size === "sm"
        ? "size-9 text-xs"
        : "size-14 text-lg"

  const color = severityColorVar(severity)

  return (
    <div
      className={cn(
        "relative grid place-items-center rounded-full font-mono font-semibold tabular-nums",
        dims,
        className,
      )}
      style={{
        background: `conic-gradient(${color} ${score * 3.6}deg, #E5E5E5 0deg)`,
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
  new: "text-accent bg-accent-soft border-accent/20",
  reviewing: "text-[#A46A16] bg-[#FDF6E2] border-[#F2DF99]",
  escalated: "text-[#B85D1B] bg-[#FDF0E6] border-[#F6CCA9]",
  resolved: "text-[#2F6B4F] bg-[#EAF3EE] border-[#C5DECF]",
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
        "inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider capitalize",
        statusStyles[status],
        className,
      )}
    >
      {status}
    </span>
  )
}

const entityStyles: Record<EntityType, string> = {
  transaction: "text-accent bg-accent-soft border-accent/20",
  wallet: "text-fg-muted bg-panel-2 border-line",
  exchange: "text-[#2F6B4F] bg-[#EAF3EE] border-[#C5DECF]",
  mixer: "text-[#A63D3D] bg-[#FDF0F0] border-[#F4BCBC]",
  ip: "text-[#A46A16] bg-[#FDF6E2] border-[#F2DF99]",
  network: "text-[#60758C] bg-panel-2 border-line",
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
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        entityStyles[type] || "text-fg-muted bg-panel-2 border-line",
        className,
      )}
    >
      {type}
    </span>
  )
}
