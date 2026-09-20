import { useNavigate } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import type { Alert, AlertStatus } from "@/data/types"
import {
  AlertTypeBadge,
  EntityTypeBadge,
  SeverityBadge,
  StatusBadge,
  severityColorVar,
} from "@/components/ui/badges"
import { formatTime } from "@/lib/utils"

export function AlertTable({
  alerts,
  compact = false,
  onStatusChange,
}: {
  alerts: Alert[]
  compact?: boolean
  onStatusChange?: (alertId: string, newStatus: AlertStatus) => void
}) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
            <th className="px-5 py-3 font-sans">Entity / TXID</th>
            {!compact ? <th className="px-4 py-3 font-sans">Type</th> : null}
            <th className="px-4 py-3 font-sans">Risk</th>
            <th className="px-4 py-3 font-sans">Severity</th>
            {!compact ? (
              <th className="px-4 py-3 font-sans">Reason / Typology</th>
            ) : null}
            <th className="px-4 py-3 font-sans">Time</th>
            {!compact ? (
              <th className="px-4 py-3 font-sans">Status</th>
            ) : null}
            <th className="px-4 py-3 text-right font-sans">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line-soft text-xs">
          {alerts.map((a) => (
            <tr
              key={a.id}
              onClick={() => navigate(`/investigation/${a.entityId}?entityType=${a.entityType}`)}
              className="group cursor-pointer transition-colors hover:bg-accent-soft/30"
            >
              <td className="px-5 py-3.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-medium text-fg">
                    {a.entityLabel.length > 20 ? `${a.entityLabel.slice(0, 16)}…` : a.entityLabel}
                  </span>
                  <EntityTypeBadge type={a.entityType} />
                </div>
              </td>
              {!compact ? (
                <td className="px-4 py-3.5 whitespace-nowrap">
                  <AlertTypeBadge type={a.alertType} />
                </td>
              ) : null}
              <td className="px-4 py-3.5">
                <span
                  className="font-mono font-bold tabular-nums text-xs"
                  style={{ color: severityColorVar(a.severity) }}
                >
                  {a.riskScore}
                </span>
              </td>
              <td className="px-4 py-3.5">
                <SeverityBadge severity={a.severity} />
              </td>
              {!compact ? (
                <td className="max-w-xs px-4 py-3.5 text-fg-muted font-sans truncate">
                  {a.reason}
                </td>
              ) : null}
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-[11px] text-fg-subtle">
                {formatTime(a.timestamp)}
              </td>
              {!compact ? (
                <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                  {onStatusChange ? (
                    <select
                      value={a.status}
                      onChange={(e) => onStatusChange(a.id, e.target.value as AlertStatus)}
                      aria-label={`Status for alert ${a.id}`}
                      className="rounded border border-line bg-panel px-2 py-0.5 text-[11px] font-medium text-fg uppercase tracking-wider focus:border-accent focus:outline-none cursor-pointer"
                    >
                      <option value="new">New</option>
                      <option value="acknowledged">Acknowledged</option>
                      <option value="investigating">Investigating</option>
                      <option value="escalated">Escalated</option>
                      <option value="resolved">Resolved</option>
                      <option value="dismissed">Dismissed</option>
                    </select>
                  ) : (
                    <StatusBadge status={a.status} />
                  )}
                </td>
              ) : null}
              <td className="px-4 py-3.5 text-right">
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent opacity-70 group-hover:opacity-100 transition-opacity">
                  Inspect <ChevronRight className="size-3.5" />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
