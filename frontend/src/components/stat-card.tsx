import type { ComponentType } from "react"
import { ArrowDownRight, ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatNumber } from "@/lib/utils"

export function StatCard({
  label,
  value,
  sublabel,
  icon: Icon,
  accent = "default",
  onClick,
}: {
  label: string
  value: number | string
  sublabel?: string
  icon?: ComponentType<{ className?: string }>
  accent?: "default" | "critical" | "high" | "accent"
  onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                if (e.key === " ") {
                  e.preventDefault()
                }
                onClick()
              }
            }
          : undefined
      }
      className={cn(
        "rounded-lg border border-line bg-panel p-5 shadow-xs transition-colors",
        onClick && "cursor-pointer hover:border-gray-300 hover:bg-[#FAFAFA]",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted font-sans">
          {label}
        </span>
        {Icon ? <Icon className="size-4 text-fg-subtle" /> : null}
      </div>
      <p className="mt-3 font-sans text-2xl font-bold tracking-tight text-fg tabular-nums">
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      {sublabel ? (
        <p className="mt-1 text-xs text-fg-subtle font-sans">{sublabel}</p>
      ) : null}
    </div>
  )
}
