import { useEffect, useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Bell, Filter, Search, RefreshCw } from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelHeader } from "@/components/ui/panel"
import { AlertTable } from "@/components/alert-table"
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states"
import { getAlerts } from "@/data/service"
import type { Alert, AlertStatus, EntityType, Severity } from "@/data/types"
import { cn } from "@/lib/utils"

const severities: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"]
const statuses: (AlertStatus | "all")[] = [
  "all",
  "new",
  "reviewing",
  "escalated",
  "resolved",
  "dismissed",
]
const entityTypes: (EntityType | "all")[] = ["all", "transaction", "wallet", "mixer", "exchange", "ip"]

type SortKey = "risk" | "time"

export function AlertsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [alerts, setAlerts] = useState<Alert[] | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [severity, setSeverity] = useState<Severity | "all">(
    (searchParams.get("severity") as Severity) || "all",
  )
  const [status, setStatus] = useState<AlertStatus | "all">(
    (searchParams.get("status") as AlertStatus) || "all",
  )
  const [type, setType] = useState<EntityType | "all">(
    (searchParams.get("entityType") as EntityType) || "all",
  )
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "")
  const [minRisk, setMinRisk] = useState(0)
  const [sort, setSort] = useState<SortKey>("risk")

  function loadAlerts() {
    setLoading(true)
    setErrorMsg(null)
    getAlerts()
      .then((data) => {
        setAlerts(data)
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load alerts from backend")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadAlerts()
  }, [])

  const filtered = useMemo(() => {
    if (!alerts) return []
    return alerts
      .filter((a) => (severity === "all" ? true : a.severity === severity))
      .filter((a) => (status === "all" ? true : a.status === status))
      .filter((a) => (type === "all" ? true : a.entityType === type))
      .filter((a) => a.riskScore >= minRisk)
      .filter((a) => {
        if (!searchQuery) return true
        const q = searchQuery.toLowerCase()
        return (
          a.entityId.toLowerCase().includes(q) ||
          a.reason.toLowerCase().includes(q) ||
          a.entityLabel.toLowerCase().includes(q) ||
          a.id.toLowerCase().includes(q)
        )
      })
      .sort((a, b) =>
        sort === "risk"
          ? b.riskScore - a.riskScore
          : new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )
  }, [alerts, severity, status, type, minRisk, searchQuery, sort])

  return (
    <AppLayout title="Alerts">
      {errorMsg ? (
        <ErrorState
          title="Failed to load alerts"
          description={errorMsg}
        />
      ) : !alerts ? (
        <LoadingState label="Loading investigation queue" />
      ) : (
        <div className="space-y-4">
          <Panel>
            <PanelHeader
              title="Filters"
              icon={<Filter className="size-4" />}
              action={
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-fg-subtle">Sort</span>
                  <div className="flex overflow-hidden rounded border border-line">
                    <SortButton active={sort === "risk"} onClick={() => setSort("risk")}>
                      Risk
                    </SortButton>
                    <SortButton active={sort === "time"} onClick={() => setSort("time")}>
                      Time
                    </SortButton>
                  </div>
                </div>
              }
            />
            <div className="space-y-3 p-4">
              {/* Search Bar */}
              <div className="relative mb-2">
                <Search className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search alert by entity ID, message, or alert ID..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs font-mono-id bg-panel-2 border border-line rounded focus:border-accent focus:outline-none text-fg placeholder:text-fg-subtle"
                />
              </div>

              <FilterRow label="Severity">
                {severities.map((s) => (
                  <Chip key={s} active={severity === s} onClick={() => setSeverity(s)}>
                    {s}
                  </Chip>
                ))}
              </FilterRow>
              <FilterRow label="Status">
                {statuses.map((s) => (
                  <Chip key={s} active={status === s} onClick={() => setStatus(s)}>
                    {s}
                  </Chip>
                ))}
              </FilterRow>
              <FilterRow label="Entity">
                {entityTypes.map((t) => (
                  <Chip key={t} active={type === t} onClick={() => setType(t)}>
                    {t}
                  </Chip>
                ))}
              </FilterRow>
              <FilterRow label={`Min risk: ${minRisk}`}>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={minRisk}
                  onChange={(e) => setMinRisk(Number(e.target.value))}
                  className="h-1.5 w-56 cursor-pointer appearance-none rounded-full bg-panel-2 accent-accent"
                  aria-label="Minimum risk score"
                />
              </FilterRow>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title="Investigation Queue"
              subtitle={`${filtered.length} of ${alerts.length} alerts`}
              icon={<Bell className="size-4" />}
            />
            {filtered.length ? (
              <AlertTable alerts={filtered} />
            ) : (
              <EmptyState
                title="No alerts match your filters"
                description="Try widening severity, status, or lowering the minimum risk threshold."
              />
            )}
          </Panel>
        </div>
      )}
    </AppLayout>
  )
}

function FilterRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="w-24 shrink-0 text-xs font-medium text-fg-subtle">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-1.5">{children}</div>
    </div>
  )
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded border px-2.5 py-1 text-xs font-medium capitalize transition-colors",
        active
          ? "border-accent/40 bg-accent-soft text-accent"
          : "border-line bg-panel-2 text-fg-muted hover:text-fg",
      )}
    >
      {children}
    </button>
  )
}

function SortButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "px-2.5 py-1 font-medium transition-colors",
        active ? "bg-accent-soft text-accent" : "bg-panel-2 text-fg-muted hover:text-fg",
      )}
    >
      {children}
    </button>
  )
}
