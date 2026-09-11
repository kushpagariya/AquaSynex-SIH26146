import { useNavigate } from "react-router-dom"
import {
  ArrowLeftRight,
  UserPlus,
  Zap,
  Network,
  ShieldAlert,
  Flag,
} from "lucide-react"
import type { TimelineEvent, TimelineKind } from "@/data/types"
import { severityColorVar } from "@/components/ui/badges"
import { formatTime, cn } from "@/lib/utils"

const kindIcon: Record<TimelineKind, typeof Zap> = {
  transaction: ArrowLeftRight,
  counterparty: UserPlus,
  burst: Zap,
  network: Network,
  "high-risk": ShieldAlert,
  flag: Flag,
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  const navigate = useNavigate()

  if (!events.length) {
    return <p className="text-sm text-fg-subtle">No timeline events recorded.</p>
  }

  return (
    <ol className="relative space-y-4 pl-2">
      <span className="absolute bottom-2 left-[13px] top-2 w-px bg-line" />
      {events.map((event) => {
        const Icon = kindIcon[event.kind]
        const color = event.severity
          ? severityColorVar(event.severity)
          : "var(--color-accent)"
        return (
          <li key={event.id} className="relative flex gap-3">
            <span
              className="relative z-10 mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border bg-panel"
              style={{ borderColor: color }}
            >
              <Icon className="size-3" style={{ color }} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono-id text-xs text-fg-subtle">
                  {formatTime(event.timestamp)}
                </span>
                <span className="text-sm font-medium text-fg">
                  {event.title}
                </span>
              </div>
              <p className="text-xs text-fg-muted">{event.detail}</p>
              {event.txid ? (
                <button
                  type="button"
                  onClick={() => navigate(`/transaction/${event.txid}`)}
                  className={cn(
                    "mt-1 font-mono-id text-xs text-accent hover:underline",
                  )}
                >
                  View transaction →
                </button>
              ) : null}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
