import { useNavigate } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import type { Alert } from "@/data/types"
import {
  EntityTypeBadge,
  SeverityBadge,
  StatusBadge,
  severityColorVar,
} from "@/components/ui/badges"
import { formatTime } from "@/lib/utils"

export function AlertTable({
  alerts,
  compact = false,
}: {
  alerts: Alert[]
  compact?: boolean
}) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-subtle">
            <th className="px-4 py-2.5 font-medium">Entity</th>
            <th className="px-4 py-2.5 font-medium">Risk</th>
            <th className="px-4 py-2.5 font-medium">Severity</th>
            {!compact ? (
              <th className="px-4 py-2.5 font-medium">Reason</th>
            ) : null}
            <th className="px-4 py-2.5 font-medium">Time</th>
            {!compact ? (
              <th className="px-4 py-2.5 font-medium">Status</th>
            ) : null}
            <th className="px-4 py-2.5" />
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr
              key={a.id}
              onClick={() => navigate(`/investigation/${a.entityId}`)}
              className="group cursor-pointer border-b border-line-soft transition-colors last:border-0 hover:bg-panel-2"
            >
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-fg">{a.entityLabel}</span>
                  <EntityTypeBadge type={a.entityType} />
                </div>
              </td>
              <td className="px-4 py-3">
                <span
                  className="font-mono-id font-semibold tabular-nums"
                  style={{ color: severityColorVar(a.severity) }}
                >
                  {a.riskScore}
                </span>
              </td>
              <td className="px-4 py-3">
                <SeverityBadge severity={a.severity} />
              </td>
              {!compact ? (
                <td className="max-w-xs px-4 py-3 text-fg-muted">{a.reason}</td>
              ) : null}
              <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs text-fg-subtle">
                {formatTime(a.timestamp)}
              </td>
              {!compact ? (
                <td className="px-4 py-3">
                  <StatusBadge status={a.status} />
                </td>
              ) : null}
              <td className="px-4 py-3 text-right">
                <ChevronRight className="ml-auto size-4 text-fg-subtle transition-colors group-hover:text-accent" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
