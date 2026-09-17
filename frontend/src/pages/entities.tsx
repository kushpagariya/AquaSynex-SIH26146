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
        {/* Concise Behavioral Notice */}
        <div className="flex items-center gap-2.5 rounded border border-line bg-panel px-4 py-2.5 text-xs text-fg-muted font-sans shadow-2xs">
          <Info className="size-3.5 shrink-0 text-accent" />
          <span>
            <strong className="text-fg font-semibold">Behavioral Cluster Notice:</strong> Inferred via multi-input co-spending and topological graph heuristics for forensic clarity; does not prove legal ownership.
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
                placeholder="Search cluster ID, lead address, or associated address..."
                className="w-full rounded border border-line bg-panel-2 py-2 pl-9 pr-4 text-xs text-fg placeholder:text-fg-subtle focus:border-accent focus:bg-panel focus:outline-none transition-colors"
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
                  title="No Inferred Clusters Match Filters"
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
                        <th className="px-4 py-3 text-right" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line-soft text-xs">
                      {filteredClusters.map((c) => {
                        const isSelected = selectedCluster?.clusterId === c.clusterId
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
                              {formatBtc(c.totalReceived)}
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
                  title={`Cluster: ${selectedCluster.clusterId}`}
                  subtitle="Inferred topological component view"
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
                  {/* Aggregate Risk Card */}
                  <div className="rounded border border-line bg-panel-2 p-4 font-sans">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">Cluster Risk Attribution</span>
                      <SeverityBadge severity={selectedCluster.severity} />
                    </div>
                    <div className="mt-3 flex items-baseline gap-2">
                      <span
                        className="font-mono text-3xl font-bold tabular-nums"
                        style={{ color: severityColorVar(selectedCluster.severity) }}
                      >
                        {selectedCluster.highestRisk}
                      </span>
                      <span className="text-xs text-fg-subtle font-sans">/ 100 risk score</span>
                    </div>
                    <p className="mt-1.5 text-xs text-fg-muted leading-relaxed">
                      Dominant pattern: <strong className="text-fg font-semibold">{selectedCluster.dominantBehavior}</strong>
                    </p>
                  </div>

                  {/* Cluster Statistics */}
                  <div className="grid grid-cols-2 gap-3 font-sans">
                    <div className="rounded border border-line bg-panel p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Cluster Addresses</p>
                      <p className="mt-1 font-mono text-base font-bold text-fg tabular-nums">
                        {formatNumber(selectedCluster.clusterSize)}
                      </p>
                    </div>
                    <div className="rounded border border-line bg-panel p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Transaction Count</p>
                      <p className="mt-1 font-mono text-base font-bold text-fg tabular-nums">
                        {formatNumber(selectedCluster.transactionCount)}
                      </p>
                    </div>
                    <div className="rounded border border-line bg-panel p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Total Received</p>
                      <p className="mt-1 font-sans text-base font-bold text-fg tabular-nums">
                        {formatBtc(selectedCluster.totalReceived)}
                      </p>
                    </div>
                    <div className="rounded border border-line bg-panel p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Total Sent</p>
                      <p className="mt-1 font-sans text-base font-bold text-fg tabular-nums">
                        {formatBtc(selectedCluster.totalSent)}
                      </p>
                    </div>
                  </div>

                  {/* Lead Address */}
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans">
                      Topological Lead Address
                    </p>
                    <div className="mt-1 flex items-center justify-between rounded border border-line bg-panel-2 p-2.5">
                      <MonoId value={selectedCluster.leadAddress} head={10} tail={8} />
                      <button
                        type="button"
                        onClick={() => navigate(`/investigation/${selectedCluster.leadAddress}?entityType=wallet`)}
                        className="text-xs font-semibold text-accent hover:underline font-sans"
                      >
                        Investigate →
                      </button>
                    </div>
                  </div>

                  {/* Co-spending Associated Addresses List */}
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans mb-2">
                      Associated Cluster Addresses ({selectedCluster.associatedAddresses.length})
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
                            className="text-[11px] font-medium text-accent hover:underline font-sans"
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
                  title="Select a Cluster"
                  description="Click on any cluster row in the registry to inspect its co-spending composition."
                />
              </Panel>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
