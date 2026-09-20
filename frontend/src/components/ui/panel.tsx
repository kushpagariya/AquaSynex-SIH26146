import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function Panel({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-line bg-panel shadow-sm shadow-black/[0.02]",
        className,
      )}
    >
      {children}
    </section>
  )
}

export function PanelHeader({
  title,
  subtitle,
  icon,
  action,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 border-b border-line px-5 py-3.5",
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        {icon ? <span className="text-fg-muted">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="truncate text-xs font-semibold uppercase tracking-wider text-fg font-sans">{title}</h2>
          {subtitle ? (
            <p className="truncate text-xs text-fg-muted">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {action}
    </div>
  )
}

export function PanelBody({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn("p-5", className)}>{children}</div>
}
