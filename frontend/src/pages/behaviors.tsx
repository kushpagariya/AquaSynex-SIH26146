import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Layers,
  Search,
  ExternalLink,
  Info,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getBehaviorAnalytics } from "@/data/service"
import type { BehaviorAnalyticsItem } from "@/data/types"
import { formatNumber, cn } from "@/lib/utils"

function isTypologySuspicious(key: string): boolean {
  return key !== "normal" && key !== "benign_high_volume"
}

export function BehaviorsPage() {
  const navigate = useNavigate()
  const [behaviors, setBehaviors] = useState<BehaviorAnalyticsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<"all" | "suspicious" | "benign">("all")
  const [sortBy, setSortBy] = useState<"count" | "risk">("count")

  function loadBehaviors() {
    setLoading(true)
    setErrorMsg(null)
    getBehaviorAnalytics()
      .then((res) => {
        setBehaviors(res)
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load behavior analytics")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadBehaviors()
  }, [])

  // Aggregate stats
  const totalTxs = behaviors.reduce((acc, b) => acc + b.count, 0)
  const suspiciousTxs = behaviors
    .filter((b) => isTypologySuspicious(b.key))
    .reduce((acc, b) => acc + b.count, 0)
  const benignTxs = totalTxs - suspiciousTxs
  const suspiciousPercentage = totalTxs > 0 ? (suspiciousTxs / totalTxs) * 100 : 0
  const topTypology = [...behaviors].sort((a, b) => b.count - a.count)[0]

  // Filtered & sorted behaviors
  const filteredBehaviors = behaviors
    .filter((b) => {
      const isSusp = isTypologySuspicious(b.key)
      if (typeFilter === "suspicious" && !isSusp) return false
      if (typeFilter === "benign" && isSusp) return false
      if (searchQuery) {
        const q = searchQuery.toLowerCase()
        return (
          b.name.toLowerCase().includes(q) ||
          b.key.toLowerCase().includes(q) ||
          b.description.toLowerCase().includes(q)
        )
      }
      return true
    })
    .sort((a, b) => {
      if (sortBy === "risk") return b.averageRisk - a.averageRisk
      return b.count - a.count
    })

  return (
    <AppLayout title="Behavior Analytics">
      <div className="space-y-6 font-sans">
        {/* Editorial Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-line pb-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-fg">
              Behavior Analytics
            </h1>
            <p className="text-xs text-fg-muted mt-1">
              CatBoost multi-class typology classification across 11 canonical transaction behaviors.
            </p>
          </div>
          <button
            onClick={loadBehaviors}
            disabled={loading}
            className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-accent hover:border-gray-300 transition-colors disabled:opacity-50 self-start sm:self-auto"
          >
            <RefreshCw className={cn("size-3.5", loading && "animate-spin text-accent")} />
            Refresh
          </button>
        </div>

        {/* TOP: 4 Institutional Summary Metrics */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="rounded-lg border border-line bg-panel p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Classified Volume</span>
              <Layers className="size-4 text-fg-subtle" />
            </div>
            <div className="text-2xl font-bold text-fg mt-2 font-mono tabular-nums">
              {formatNumber(totalTxs)}
            </div>
            <div className="text-xs text-fg-subtle mt-1">11 typologies evaluated</div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Suspicious Flow</span>
              <AlertTriangle className="size-4 text-[#A63D3D]" />
            </div>
            <div className="text-2xl font-bold text-[#A63D3D] mt-2 font-mono tabular-nums">
              {formatNumber(suspiciousTxs)}
              <span className="text-xs text-fg-muted font-normal ml-1.5">
                ({suspiciousPercentage.toFixed(1)}%)
              </span>
            </div>
            <div className="text-xs text-fg-subtle mt-1">Burst, peeling, mixing, etc.</div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Benign Baseline</span>
              <CheckCircle2 className="size-4 text-[#2F6B4F]" />
            </div>
            <div className="text-2xl font-bold text-[#2F6B4F] mt-2 font-mono tabular-nums">
              {formatNumber(benignTxs)}
              <span className="text-xs text-fg-muted font-normal ml-1.5">
                ({(100 - suspiciousPercentage).toFixed(1)}%)
              </span>
            </div>
            <div className="text-xs text-fg-subtle mt-1">Standard UTXO transaction flow</div>
          </div>

          <div className="rounded-lg border border-line bg-panel p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">Dominant Typology</span>
              <TrendingUp className="size-4 text-accent" />
            </div>
            <div className="text-base font-bold text-fg mt-2 truncate">
              {topTypology ? topTypology.name : "N/A"}
            </div>
            <div className="text-xs text-fg-subtle mt-1">
              {topTypology ? `${formatNumber(topTypology.count)} txs (${topTypology.percentage.toFixed(1)}%)` : "No data"}
            </div>
          </div>
        </div>

        {/* MIDDLE: Behavior Distribution Chart */}
        <Panel>
          <PanelHeader
            title="Typology Volume Distribution"
            subtitle="Proportional share of transactions by detected behavior motif"
            icon={<Layers className="size-4" />}
          />
          <PanelBody className="space-y-4">
            {/* Proportional Segmented Bar */}
            <div className="h-4 w-full overflow-hidden rounded bg-panel-2 border border-line flex">
              {behaviors.map((b) => {
                if (b.percentage <= 0) return null
                const isSusp = isTypologySuspicious(b.key)
                return (
                  <div
                    key={b.key}
                    style={{ width: `${b.percentage}%` }}
                    className={cn(
                      "h-full transition-all duration-300 relative group cursor-pointer",
                      isSusp ? "bg-[#A63D3D] hover:bg-[#8B2626]" : "bg-[#173B63] hover:bg-[#0F2844]",
                    )}
                    title={`${b.name}: ${b.count} txs (${b.percentage.toFixed(1)}%)`}
                  />
                )
              })}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-fg-muted pt-1">
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm bg-[#173B63]" />
                Standard / Normal Flow ({benignTxs} txs)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-sm bg-[#A63D3D]" />
                Suspicious Laundering Motifs ({suspiciousTxs} txs)
              </span>
            </div>
          </PanelBody>
        </Panel>

        {/* Filter Toolbar */}
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="relative min-w-[260px] flex-1">
              <Search className="absolute left-3 top-2.5 size-3.5 text-fg-subtle" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search typology name or key..."
                className="w-full rounded border border-line bg-panel-2 py-1.5 pl-9 pr-3 text-xs text-fg focus:border-accent focus:bg-panel focus:outline-none transition-colors"
              />
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center rounded border border-line bg-panel p-0.5 text-xs">
                <button
                  onClick={() => setTypeFilter("all")}
                  className={cn(
                    "px-2.5 py-1 rounded transition-colors font-medium",
                    typeFilter === "all" ? "bg-accent text-white" : "text-fg-muted hover:text-fg",
                  )}
                >
                  All (11)
                </button>
                <button
                  onClick={() => setTypeFilter("suspicious")}
                  className={cn(
                    "px-2.5 py-1 rounded transition-colors font-medium",
                    typeFilter === "suspicious" ? "bg-accent text-white" : "text-fg-muted hover:text-fg",
                  )}
                >
                  Suspicious
                </button>
                <button
                  onClick={() => setTypeFilter("benign")}
                  className={cn(
                    "px-2.5 py-1 rounded transition-colors font-medium",
                    typeFilter === "benign" ? "bg-accent text-white" : "text-fg-muted hover:text-fg",
                  )}
                >
                  Normal
                </button>
              </div>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "count" | "risk")}
                className="rounded border border-line bg-panel px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none"
              >
                <option value="count">Sort: Volume</option>
                <option value="risk">Sort: Avg Risk</option>
              </select>
            </div>
          </div>
        </Panel>

        {/* BOTTOM: Dense Institutional Behavior Table */}
        <Panel>
          <PanelHeader
            title="Typologies Classification Ledger"
            subtitle={`Showing ${filteredBehaviors.length} of ${behaviors.length} canonical behavioral classes`}
            icon={<Layers className="size-4" />}
          />

          {loading ? (
            <LoadingState label="Evaluating behavioral typologies" />
          ) : errorMsg ? (
            <ErrorState title="Failed to load typologies" description={errorMsg} />
          ) : filteredBehaviors.length === 0 ? (
            <EmptyState
              title="No Typologies Match Criteria"
              description="Clear search or reset category filters."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                    <th className="px-5 py-3 font-sans">Behavior Typology</th>
                    <th className="px-4 py-3 font-sans">Count</th>
                    <th className="px-4 py-3 font-sans">Network Share</th>
                    <th className="px-4 py-3 font-sans">Average Risk</th>
                    <th className="px-4 py-3 text-right font-sans">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft text-xs">
                  {filteredBehaviors.map((item) => {
                    const isSusp = isTypologySuspicious(item.key)
                    const riskScore = item.averageRisk <= 1 ? Math.round(item.averageRisk * 100) : Math.round(item.averageRisk)
                    return (
                      <tr
                        key={item.key}
                        onClick={() => navigate(`/transactions?behavior=${item.key}`)}
                        className="group cursor-pointer transition-colors hover:bg-accent-soft/30"
                      >
                        <td className="px-5 py-3.5">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-fg text-xs font-sans">
                                {item.name}
                              </span>
                              <span
                                className={cn(
                                  "px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider border",
                                  isSusp
                                    ? "bg-[#FDF0F0] text-[#A63D3D] border-[#F4BCBC]"
                                    : "bg-[#EAF3EE] text-[#2F6B4F] border-[#C5DECF]",
                                )}
                              >
                                {isSusp ? "Suspicious" : "Normal"}
                              </span>
                            </div>
                            <p className="text-[11px] text-fg-muted mt-0.5 max-w-md truncate">
                              {item.description}
                            </p>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 font-mono font-medium text-xs text-fg tabular-nums">
                          {formatNumber(item.count)}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-fg-muted tabular-nums">
                          {item.percentage.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs font-bold tabular-nums">
                          <span
                            style={{
                              color:
                                riskScore >= 70
                                  ? "#A63D3D"
                                  : riskScore >= 50
                                    ? "#B85D1B"
                                    : riskScore >= 30
                                      ? "#A46A16"
                                      : "#2F6B4F",
                            }}
                          >
                            {riskScore}%
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent opacity-80 group-hover:opacity-100 font-sans hover:underline">
                            Filter Transactions <ExternalLink className="size-3" />
                          </span>
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
    </AppLayout>
  )
}
