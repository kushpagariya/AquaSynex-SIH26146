import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  Users,
  Search,
  RefreshCw,
  ShieldAlert,
  Info,
  ChevronRight,
  Share2,
  Bell,
  AlertTriangle,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getInferredClusters } from "@/data/service"
import type { InferredCluster, Severity } from "@/data/types"
import { formatBtc, formatNumber, cn } from "@/lib/utils"

export function EntitiesPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusClusterParam = searchParams.get("cluster") || searchParams.get("focus") || ""

  const [clusters, setClusters] = useState<InferredCluster[] | null>(null)
  const [selectedCluster, setSelectedCluster] = useState<InferredCluster | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all")

  function loadClusters() {
    setLoading(true)
    setErrorMsg(null)
    getInferredClusters()
      .then((res) => {
        setClusters(res)
        if (res.length > 0) {
          const match = focusClusterParam
            ? res.find(
                (c) =>
                  c.clusterId.toLowerCase() === focusClusterParam.toLowerCase() ||
                  c.leadAddress.toLowerCase().includes(focusClusterParam.toLowerCase()) ||
                  c.associatedAddresses.some((a) => a.toLowerCase().includes(focusClusterParam.toLowerCase())),
              )
            : null
          setSelectedCluster(match || res[0])
        } else {
          setSelectedCluster(null)
        }
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load inferred clusters")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadClusters()
  }, [])

  const filteredClusters = (clusters || []).filter((c) => {
    if (severityFilter !== "all" && c.severity !== severityFilter) return false
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      c.clusterId.toLowerCase().includes(q) ||
      c.leadAddress.toLowerCase().includes(q) ||
      c.associatedAddresses.some((a) => a.toLowerCase().includes(q))
    )
  })

  return (
    <AppLayout title="Inferred Behavioral Clusters">
      <div className="space-y-6">
        {/* Concise Behavioral Notice */}
        <div className="flex items-center gap-2.5 rounded border border-line bg-panel px-4 py-2.5 text-xs text-fg-muted font-sans shadow-2xs">
          <Info className="size-3.5 shrink-0 text-accent" />
          <span>
            Clusters are inferred from transaction and graph relationships and do not establish ownership.
          </span>
        </div>

        {/* Filter & Search Bar */}
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 font-sans">
            <div className="relative min-w-[280px] flex-1">
              <Search className="absolute left-3 top-2.5 size-3.5 text-fg-subtle" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search cluster ID, lead/representative address, or associated address..."
                className="w-full rounded border border-line bg-panel-2 py-2 pl-9 pr-4 text-xs text-fg placeholder:text-fg-subtle focus:border-accent focus:bg-panel focus:outline-none transition-colors font-sans"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Risk Filter:</span>
              {(["all", "critical", "high", "medium", "low"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverityFilter(s)}
                  className={cn(
                    "rounded border px-2.5 py-1 text-xs font-medium capitalize transition-colors font-sans",
                    severityFilter === s
                      ? "border-accent bg-accent-soft text-accent font-semibold"
                      : "border-line bg-panel text-fg-muted hover:text-fg hover:border-gray-300",
                  )}
                >
                  {s}
                </button>
              ))}
              <button
                type="button"
                onClick={loadClusters}
                className="ml-2 flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-accent hover:border-gray-300 transition-colors"
              >
                <RefreshCw className="size-3.5" />
                Refresh
              </button>
            </div>
          </div>
        </Panel>

        {/* Main Grid: Clusters Register & Detailed Split Pane */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          {/* Clusters Table (7 Cols on desktop) */}
          <div className="xl:col-span-7">
            <Panel>
              <PanelHeader
                title="Inferred Behavioral Clusters"
                subtitle={`${filteredClusters.length} clusters identified in active dataset`}
                icon={<Users className="size-4" />}
              />
              {loading ? (
                <LoadingState label="Computing canonical cluster topologies" />
              ) : errorMsg ? (
                <ErrorState title="Failed to load clusters" description={errorMsg} />
              ) : !filteredClusters.length ? (
                <EmptyState
                  title="No behavioral clusters found in the active dataset."
                  description="Adjust your search term or severity criteria."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left font-sans">
                    <thead>
                      <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                        <th className="px-5 py-3">Cluster ID</th>
                        <th className="px-4 py-3">Addresses</th>
                        <th className="px-4 py-3">Transactions</th>
                        <th className="px-4 py-3">Volume</th>
                        <th className="px-4 py-3">Risk</th>
                        <th className="px-4 py-3">Dominant Behavior</th>
                        <th className="px-4 py-3">Alerts</th>
                        <th className="px-4 py-3 text-right" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line-soft text-xs">
                      {filteredClusters.map((c) => {
                        const isSelected = selectedCluster?.clusterId === c.clusterId
                        const totalVol = Number((c.totalReceived + c.totalSent).toFixed(4))
                        return (
                          <tr
                            key={c.clusterId}
                            onClick={() => setSelectedCluster(c)}
                            className={cn(
                              "group cursor-pointer transition-colors",
                              isSelected ? "bg-accent-soft/40 border-l-2 border-l-accent" : "hover:bg-accent-soft/20",
                            )}
                          >
                            <td className="px-5 py-3.5 font-mono text-xs font-semibold text-fg">
                              {c.clusterId}
                            </td>
                            <td className="px-4 py-3.5 font-mono text-xs tabular-nums text-fg-muted">
                              {formatNumber(c.clusterSize)}
                            </td>
                            <td className="px-4 py-3.5 font-mono text-xs tabular-nums text-fg-muted">
                              {formatNumber(c.transactionCount)}
                            </td>
                            <td className="whitespace-nowrap px-4 py-3.5 font-sans font-semibold tabular-nums text-fg">
                              {formatBtc(totalVol)}
                            </td>
                            <td className="px-4 py-3.5 font-mono font-bold tabular-nums">
                              <span style={{ color: severityColorVar(c.severity) }}>
                                {c.highestRisk}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span className="inline-flex items-center rounded border border-line bg-panel-2 px-2 py-0.5 text-[11px] font-medium text-fg">
                                {c.dominantBehavior}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span
                                className={cn(
                                  "inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium font-sans",
                                  c.activeAlertCount > 0
                                    ? "border border-red-200 bg-red-50 text-red-700 font-semibold"
                                    : "border border-line bg-panel-2 text-fg-muted",
                                )}
                              >
                                <Bell className="size-3" />
                                {c.activeAlertCount > 0
                                  ? `${c.activeAlertCount} active`
                                  : `${c.totalAlertCount || 0} alerts`}
                              </span>
                            </td>
                            <td className="px-4 py-3.5 text-right text-fg-subtle">
                              <ChevronRight className="size-4" />
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>
          </div>

          {/* Cluster Inspector Split Pane (5 Cols on desktop) */}
          <div className="xl:col-span-5">
            {selectedCluster ? (
              <Panel className="sticky top-6">
                <PanelHeader
                  title={`Cluster ${selectedCluster.clusterId}`}
                  subtitle="Inferred behavioral cluster summary"
                  icon={<ShieldAlert className="size-4" />}
                  action={
                    <button
                      type="button"
                      onClick={() => navigate(`/graph?focus=${selectedCluster.leadAddress}`)}
                      className="flex items-center gap-1 text-xs font-semibold text-accent hover:underline font-sans"
                    >
                      <Share2 className="size-3.5" />
                      View in Graph
                    </button>
                  }
                />
                <PanelBody className="space-y-5">
                  {/* 1. CLUSTER RISK & DOMINANT BEHAVIOR */}
                  <div className="rounded border border-line bg-panel-2 p-4 font-sans">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
                        CLUSTER RISK
                      </span>
                      <SeverityBadge severity={selectedCluster.severity} />
                    </div>
                    <div className="mt-3 flex items-baseline gap-2">
                      <span
                        className="font-mono text-3xl font-bold tabular-nums"
                        style={{ color: severityColorVar(selectedCluster.severity) }}
                      >
                        {selectedCluster.highestRisk}
                      </span>
                      <span className="text-xs text-fg-subtle font-sans">/ 100</span>
                      <span
                        className="text-xs font-bold uppercase font-sans tracking-wide ml-1"
                        style={{ color: severityColorVar(selectedCluster.severity) }}
                      >
                        {selectedCluster.severity}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-fg-subtle font-sans">
                      Aggregated from member transaction risk
                    </p>
                    <div className="mt-3 pt-3 border-t border-line flex items-center justify-between">
                      <span className="text-xs text-fg-muted">Dominant behavior:</span>
                      <span className="inline-flex items-center rounded border border-line bg-panel px-2.5 py-0.5 text-xs font-semibold text-fg">
                        {selectedCluster.dominantBehavior}
                      </span>
                    </div>
                  </div>

                  {/* 2. ACTIVE ALERTS */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans flex items-center gap-1.5">
                        <AlertTriangle className="size-3.5 text-amber-500" />
                        ACTIVE ALERTS ({selectedCluster.activeAlertCount || 0})
                      </p>
                      {selectedCluster.activeAlertCount > 0 && (
                        <span className="rounded bg-red-100 px-1.5 py-0.2 text-[10px] font-semibold text-red-700">
                          {selectedCluster.activeAlertCount} active
                        </span>
                      )}
                    </div>

                    {selectedCluster.alerts && selectedCluster.alerts.length > 0 ? (
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {selectedCluster.alerts.map((al) => (
                          <div
                            key={al.alertId}
                            className="rounded border border-line bg-panel p-2.5 font-sans space-y-1.5 shadow-2xs"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <MonoId value={al.alertId} head={10} tail={6} />
                              <span className="font-mono text-[11px] font-bold text-fg">
                                {al.alertType}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                              <SeverityBadge severity={(al.severity?.toLowerCase() as Severity) || "medium"} />
                              <span className="rounded border border-line bg-panel-2 px-1.5 py-0.5 text-[10px] font-mono font-bold text-fg">
                                {al.priority}
                              </span>
                              <span className="rounded border border-line bg-panel-2 px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase text-accent">
                                {al.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded border border-dashed border-line bg-panel-2/50 px-3 py-3 text-center text-xs text-fg-subtle font-sans">
                        No active alerts associated with this cluster.
                      </div>
                    )}
                  </div>

                  {/* 3. CLUSTER SUMMARY */}
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans mb-2">
                      CLUSTER SUMMARY
                    </p>
                    <div className="grid grid-cols-2 gap-2.5 font-sans">
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Addresses</p>
                        <p className="mt-0.5 font-mono text-base font-bold text-fg tabular-nums">
                          {formatNumber(selectedCluster.clusterSize)}
                        </p>
                      </div>
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Transactions</p>
                        <p className="mt-0.5 font-mono text-base font-bold text-fg tabular-nums">
                          {formatNumber(selectedCluster.transactionCount)}
                        </p>
                      </div>
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Total Received</p>
                        <p className="mt-0.5 font-sans text-sm font-bold text-fg tabular-nums">
                          {formatBtc(selectedCluster.totalReceived)}
                        </p>
                      </div>
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Total Sent</p>
                        <p className="mt-0.5 font-sans text-sm font-bold text-fg tabular-nums">
                          {formatBtc(selectedCluster.totalSent)}
                        </p>
                      </div>
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Aggregate Volume</p>
                        <p className="mt-0.5 font-sans text-sm font-bold text-fg tabular-nums">
                          {formatBtc(Number((selectedCluster.totalReceived + selectedCluster.totalSent).toFixed(4)))}
                        </p>
                      </div>
                      <div className="rounded border border-line bg-panel p-2.5">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Active Alerts</p>
                        <p className={cn("mt-0.5 font-mono text-base font-bold tabular-nums", selectedCluster.activeAlertCount > 0 ? "text-red-600" : "text-fg")}>
                          {selectedCluster.activeAlertCount || 0}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 4. REPRESENTATIVE ADDRESS */}
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans">
                        Representative Address
                      </p>
                      <span className="text-[10px] text-fg-subtle font-sans italic">
                        Selected by graph topology
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between rounded border border-line bg-panel-2 p-2.5">
                      <MonoId value={selectedCluster.leadAddress} head={10} tail={8} />
                      <button
                        type="button"
                        onClick={() => navigate(`/investigation/${selectedCluster.leadAddress}?entityType=wallet`)}
                        className="text-xs font-semibold text-accent hover:underline font-sans ml-2 shrink-0"
                      >
                        Investigate →
                      </button>
                    </div>
                  </div>

                  {/* 5. ASSOCIATED CLUSTER ADDRESSES */}
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans mb-2">
                      ASSOCIATED CLUSTER ADDRESSES ({selectedCluster.associatedAddresses.length})
                    </p>
                    <div className="max-h-48 overflow-y-auto rounded border border-line divide-y divide-line-soft">
                      {selectedCluster.associatedAddresses.map((addr) => (
                        <div
                          key={addr}
                          className="flex items-center justify-between px-3 py-2 text-xs hover:bg-accent-soft/20 transition-colors"
                        >
                          <MonoId value={addr} head={8} tail={6} />
                          <button
                            type="button"
                            onClick={() => navigate(`/investigation/${addr}?entityType=wallet`)}
                            className="text-[11px] font-medium text-accent hover:underline font-sans ml-2 shrink-0"
                          >
                            Profile
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </PanelBody>
              </Panel>
            ) : (
              <Panel>
                <EmptyState
                  title="Select a cluster to view its forensic summary."
                  description="Click on any cluster row in the registry to inspect its inferred behavioral composition."
                />
              </Panel>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
