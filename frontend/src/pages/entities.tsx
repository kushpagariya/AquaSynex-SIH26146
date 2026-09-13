import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  Users,
  Search,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Wallet,
  ArrowLeftRight,
  Info,
  ChevronRight,
  Share2,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getInferredClusters } from "@/data/service"
import type { InferredCluster, Severity } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber, cn } from "@/lib/utils"

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
                  c.associatedAddresses.some((a) => a.toLowerCase().includes(focusClusterParam.toLowerCase())),
              )
            : null
          setSelectedCluster(match || res[0])
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
        {/* Scientific / Forensic Honesty Banner */}
        <div className="rounded-lg border border-line bg-panel p-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded bg-accent-soft text-accent">
              <Info className="size-4" />
            </span>
            <div className="space-y-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-fg">
                Inferred Behavioral Cluster (IBC) Notice
              </h3>
              <p className="text-xs leading-relaxed text-fg-muted">
                Clusters represent algorithmic groupings derived from multi-input co-spending and topological graph
                adjacency heuristics. They aggregate transaction telemetry for forensic clarity and{" "}
                <strong className="text-fg">do NOT prove real-world identity, legal ownership, or criminal culpability</strong>.
                Risk scores reflect the{" "}
                <span className="text-accent font-medium">Aggregate ML Risk from Associated Transactions</span>.
              </p>
            </div>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div className="relative min-w-[280px] flex-1">
              <Search className="absolute left-3 top-2.5 size-4 text-fg-subtle" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search cluster ID, lead address, or associated address..."
                className="w-full rounded-md border border-line bg-panel-2 py-2 pl-9 pr-4 text-xs font-mono-id text-fg placeholder:text-fg-subtle focus:border-accent focus:outline-none"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-fg-subtle">Filter Risk:</span>
              {(["all", "critical", "high", "medium", "low"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverityFilter(s)}
                  className={cn(
                    "rounded border px-2.5 py-1 text-xs font-medium capitalize transition-colors",
                    severityFilter === s
                      ? "border-accent/40 bg-accent-soft text-accent"
                      : "border-line bg-panel-2 text-fg-muted hover:text-fg",
                  )}
                >
                  {s}
                </button>
              ))}
              <button
                type="button"
                onClick={loadClusters}
                className="ml-2 flex items-center gap-1.5 rounded border border-line bg-panel-2 px-3 py-1.5 text-xs text-fg-muted hover:text-accent"
              >
                <RefreshCw className="size-3.5" />
                Refresh
              </button>
            </div>
          </div>
        </Panel>

        {/* Main Grid: Clusters Register & Detailed Inspector */}
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
                  title="No Inferred Clusters Match Filters"
                  description="Adjust your search term or severity criteria."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-line text-left text-[11px] uppercase tracking-wider text-fg-subtle">
                        <th className="px-4 py-2.5 font-medium">Cluster ID</th>
                        <th className="px-4 py-2.5 font-medium">Addresses</th>
                        <th className="px-4 py-2.5 font-medium">TX Count</th>
                        <th className="px-4 py-2.5 font-medium">Received (BTC)</th>
                        <th className="px-4 py-2.5 font-medium">Max ML Risk</th>
                        <th className="px-4 py-2.5 font-medium">Typology</th>
                        <th className="px-4 py-2.5" />
                      </tr>
                    </thead>
                    <tbody>
                      {filteredClusters.map((c) => {
                        const isSelected = selectedCluster?.clusterId === c.clusterId
                        return (
                          <tr
                            key={c.clusterId}
                            onClick={() => setSelectedCluster(c)}
                            className={cn(
                              "group cursor-pointer border-b border-line-soft transition-colors last:border-0",
                              isSelected ? "bg-accent-soft/30 border-l-2 border-l-accent" : "hover:bg-panel-2",
                            )}
                          >
                            <td className="px-4 py-3 font-mono-id text-xs font-semibold text-fg">
                              {c.clusterId}
                            </td>
                            <td className="px-4 py-3 font-mono-id text-xs tabular-nums text-fg-muted">
                              {formatNumber(c.clusterSize)}
                            </td>
                            <td className="px-4 py-3 font-mono-id text-xs tabular-nums text-fg-muted">
                              {formatNumber(c.transactionCount)}
                            </td>
                            <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs tabular-nums text-fg">
                              {formatBtc(c.totalReceived)}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className="font-mono-id text-xs font-semibold tabular-nums"
                                  style={{ color: severityColorVar(c.severity) }}
                                >
                                  {c.highestRisk}
                                </span>
                                <SeverityBadge severity={c.severity} />
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="inline-block rounded border border-line bg-panel-2 px-2 py-0.5 font-mono-id text-[10px] text-fg-subtle">
                                {c.dominantBehavior}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <ChevronRight className={cn("ml-auto size-4 transition-colors", isSelected ? "text-accent" : "text-fg-subtle group-hover:text-fg")} />
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

          {/* Cluster Inspector Details (5 Cols on desktop) */}
          <div className="xl:col-span-5">
            {selectedCluster ? (
              <Panel className="sticky top-6">
                <PanelHeader
                  title={`Cluster Details: ${selectedCluster.clusterId}`}
                  subtitle="Inferred topological component view"
                  icon={<ShieldAlert className="size-4" />}
                  action={
                    <button
                      type="button"
                      onClick={() => navigate(`/graph?focus=${selectedCluster.leadAddress}`)}
                      className="flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                    >
                      <Share2 className="size-3.5" />
                      View in Graph
                    </button>
                  }
                />
                <PanelBody className="space-y-5">
                  {/* Aggregate Risk Card */}
                  <div className="rounded-md border border-line bg-panel-2 p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-fg-subtle uppercase tracking-wider">
                        Aggregate ML Risk
                      </span>
                      <SeverityBadge severity={selectedCluster.severity} />
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span
                        className="font-mono-id text-2xl font-bold tabular-nums"
                        style={{ color: severityColorVar(selectedCluster.severity) }}
                      >
                        {selectedCluster.highestRisk} / 100
                      </span>
                      <span className="text-xs text-fg-subtle">
                        (Average: {selectedCluster.averageRisk} / 100)
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-fg-subtle">
                      Derived from associated transactions evaluated by the transaction-level XGBoost detector.
                    </p>
                  </div>

                  {/* Volume & Activity Metrics */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded border border-line-soft bg-panel-2/50 p-2.5">
                      <p className="text-[11px] text-fg-subtle">Total Received</p>
                      <p className="mt-1 font-mono-id text-sm font-semibold text-fg">
                        {formatBtc(selectedCluster.totalReceived)}
                      </p>
                    </div>
                    <div className="rounded border border-line-soft bg-panel-2/50 p-2.5">
                      <p className="text-[11px] text-fg-subtle">Total Sent</p>
                      <p className="mt-1 font-mono-id text-sm font-semibold text-fg">
                        {formatBtc(selectedCluster.totalSent)}
                      </p>
                    </div>
                    <div className="rounded border border-line-soft bg-panel-2/50 p-2.5">
                      <p className="text-[11px] text-fg-subtle">Addresses in Cluster</p>
                      <p className="mt-1 font-mono-id text-sm font-semibold text-fg">
                        {selectedCluster.clusterSize}
                      </p>
                    </div>
                    <div className="rounded border border-line-soft bg-panel-2/50 p-2.5">
                      <p className="text-[11px] text-fg-subtle">Transactions</p>
                      <p className="mt-1 font-mono-id text-sm font-semibold text-fg">
                        {selectedCluster.transactionCount}
                      </p>
                    </div>
                  </div>

                  {/* Cluster Timestamps */}
                  <div className="space-y-1 rounded border border-line-soft bg-panel-2/30 p-2.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-fg-subtle">First Seen:</span>
                      <span className="font-mono-id text-fg">
                        {selectedCluster.firstSeen ? formatDateTime(selectedCluster.firstSeen) : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-fg-subtle">Last Seen:</span>
                      <span className="font-mono-id text-fg">
                        {selectedCluster.lastSeen ? formatDateTime(selectedCluster.lastSeen) : "—"}
                      </span>
                    </div>
                  </div>

                  {/* Associated Addresses */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-fg-subtle">
                        Associated Addresses ({selectedCluster.associatedAddresses.length})
                      </h4>
                    </div>
                    <div className="max-h-48 space-y-1.5 overflow-y-auto pr-1">
                      {selectedCluster.associatedAddresses.map((addr) => (
                        <div
                          key={addr}
                          className="flex items-center justify-between rounded border border-line-soft bg-panel-2 px-2.5 py-1.5 text-xs"
                        >
                          <MonoId value={addr} head={10} tail={8} />
                          <button
                            type="button"
                            onClick={() => navigate(`/investigation/${addr}?entityType=wallet`)}
                            className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline"
                          >
                            Investigate
                            <ExternalLink className="size-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 border-t border-line-soft pt-3">
                    <button
                      type="button"
                      onClick={() => navigate(`/investigation/${selectedCluster.leadAddress}?entityType=wallet`)}
                      className="flex-1 rounded-md border border-accent/40 bg-accent-soft py-2 text-xs font-medium text-accent hover:bg-accent/10"
                    >
                      Investigate Lead Address →
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate(`/transactions?search=${selectedCluster.clusterId}`)}
                      className="flex items-center gap-1.5 rounded-md border border-line bg-panel-2 px-3 py-2 text-xs text-fg hover:text-accent"
                    >
                      <ArrowLeftRight className="size-3.5" />
                      TXs
                    </button>
                  </div>
                </PanelBody>
              </Panel>
            ) : (
              <Panel>
                <PanelBody>
                  <p className="text-xs text-fg-subtle text-center py-12">
                    Select an inferred cluster from the table to view its associated addresses, volume, and topology.
                  </p>
                </PanelBody>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
