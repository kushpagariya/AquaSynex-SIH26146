import type { ReactNode } from "react"
import { AlertTriangle, Inbox, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export function LoadingState({
  label = "Loading",
  className,
}: {
  label?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-fg-subtle",
        className,
      )}
    >
      <Loader2 className="size-5 animate-spin text-accent" />
      <span className="text-sm">{label}…</span>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-center",
        className,
      )}
    >
      <span className="grid size-11 place-items-center rounded-full border border-line bg-panel-2 text-fg-subtle">
        {icon ?? <Inbox className="size-5" />}
      </span>
      <div>
        <p className="text-sm font-medium text-fg">{title}</p>
        {description ? (
          <p className="mx-auto mt-1 max-w-sm text-xs text-fg-subtle">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  )
}

export function ErrorState({
  title = "Something went wrong",
  description,
  className,
}: {
  title?: string
  description?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16 text-center",
        className,
      )}
    >
      <span className="grid size-11 place-items-center rounded-full border border-risk-critical/40 bg-risk-critical-soft text-risk-critical">
        <AlertTriangle className="size-5" />
      </span>
      <div>
        <p className="text-sm font-medium text-fg">{title}</p>
        {description ? (
          <p className="mx-auto mt-1 max-w-sm text-xs text-fg-subtle">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  )
}
