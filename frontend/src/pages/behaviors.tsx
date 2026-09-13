import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Layers,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Search,
  ExternalLink,
  Info,
  RefreshCw,
  GitFork,
  ArrowRight,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getBehaviorAnalytics } from "@/data/service"
import type { BehaviorAnalyticsItem, Severity } from "@/data/types"
import { formatBtc, formatNumber, cn } from "@/lib/utils"

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
      <div className="space-y-6">
        {/* Page Title */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-terminal-cyan uppercase tracking-wider">
                ML CLASSIFICATION ENGINE // 11 CANONICAL TYPOLOGIES
              </span>
            </div>
            <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-3">
              <Activity className="h-6 w-6 text-terminal-cyan" />
              Behavior Analytics & Typologies
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              CatBoost multiclass pattern detection across 11 behavioral typologies derived from graph motifs, temporal cadences, and transaction features.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadBehaviors}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-mono bg-panel border border-border rounded hover:border-terminal-cyan transition-colors flex items-center gap-1.5 text-foreground disabled:opacity-50"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin text-terminal-cyan")} />
              Refresh
            </button>
          </div>
        </div>

        {/* Aggregate Summary KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-panel border border-border rounded">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Classified Transactions</span>
              <Layers className="h-4 w-4 text-terminal-cyan" />
            </div>
            <div className="text-2xl font-bold font-mono text-foreground mt-2">
              {formatNumber(totalTxs)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              100% evaluated across 11 classes
            </div>
          </div>

          <div className="p-4 bg-panel border border-border rounded">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Suspicious Typologies</span>
              <AlertTriangle className="h-4 w-4 text-severity-high" />
            </div>
            <div className="text-2xl font-bold font-mono text-severity-high mt-2">
              {formatNumber(suspiciousTxs)}
              <span className="text-xs text-muted-foreground font-normal ml-2">
                ({suspiciousPercentage.toFixed(1)}%)
              </span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Peeling, burst, multihop, mixing, etc.
            </div>
          </div>

          <div className="p-4 bg-panel border border-border rounded">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Benign / Normal Flow</span>
              <CheckCircle2 className="h-4 w-4 text-severity-low" />
            </div>
            <div className="text-2xl font-bold font-mono text-severity-low mt-2">
              {formatNumber(benignTxs)}
              <span className="text-xs text-muted-foreground font-normal ml-2">
                ({(100 - suspiciousPercentage).toFixed(1)}%)
              </span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Standard UTXO and regular volume
            </div>
          </div>

          <div className="p-4 bg-panel border border-border rounded">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground uppercase">Dominant Typology</span>
              <TrendingUp className="h-4 w-4 text-terminal-cyan" />
            </div>
            <div className="text-base font-bold font-mono text-foreground mt-2 truncate">
              {topTypology ? topTypology.name : "N/A"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {topTypology ? `${formatNumber(topTypology.count)} txs (${topTypology.percentage.toFixed(1)}%)` : "No data"}
            </div>
          </div>
        </div>

        {/* Methodology & Taxonomy Disclaimer */}
        <div className="p-3.5 bg-panel/80 border border-border/80 rounded flex items-start gap-3 text-xs text-muted-foreground">
          <Info className="h-4 w-4 text-terminal-cyan flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-foreground">Forensic Inference Methodology:</span> CatBoost multiclass classification partitions transactions into 11 behavioral typologies without making definitive legal assertions. Suspicious typologies represent statistical alignment with historical laundering motifs (e.g. peeling chains, mixing patterns, synchronized bursts) and should be corroborated with network broadcast telemetry and cluster graph analysis.
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="p-4 bg-panel border border-border rounded flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Search */}
            <div className="relative flex-1 md:w-64">
              <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search typology or description..."
                className="w-full pl-9 pr-3 py-1.5 text-xs font-mono bg-background border border-border rounded focus:border-terminal-cyan focus:outline-none text-foreground placeholder:text-muted-foreground"
              />
            </div>

            {/* Type selector */}
            <div className="flex items-center gap-1 bg-background border border-border rounded p-0.5 text-xs font-mono">
              <button
                onClick={() => setTypeFilter("all")}
                className={cn(
                  "px-2.5 py-1 rounded transition-colors",
                  typeFilter === "all" ? "bg-panel text-terminal-cyan font-bold" : "text-muted-foreground hover:text-foreground",
                )}
              >
                All (11)
              </button>
              <button
                onClick={() => setTypeFilter("suspicious")}
                className={cn(
                  "px-2.5 py-1 rounded transition-colors",
                  typeFilter === "suspicious" ? "bg-panel text-severity-high font-bold" : "text-muted-foreground hover:text-foreground",
                )}
              >
                Suspicious Patterns
              </button>
              <button
                onClick={() => setTypeFilter("benign")}
                className={cn(
                  "px-2.5 py-1 rounded transition-colors",
                  typeFilter === "benign" ? "bg-panel text-severity-low font-bold" : "text-muted-foreground hover:text-foreground",
                )}
              >
                Normal / Benign
              </button>
            </div>
          </div>

          {/* Sort selector */}
          <div className="flex items-center gap-2 self-end md:self-auto text-xs font-mono text-muted-foreground">
            <span>Sort By:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "count" | "risk")}
              className="px-2.5 py-1 bg-background border border-border rounded text-foreground focus:border-terminal-cyan focus:outline-none"
            >
              <option value="count">Transaction Count</option>
              <option value="risk">Average ML Risk</option>
            </select>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && <LoadingState label="Evaluating multiclass behavioral typologies" />}
        {errorMsg && <ErrorState title="Failed to load behaviors" description={errorMsg} />}

        {!loading && !errorMsg && filteredBehaviors.length === 0 && (
          <EmptyState
            title="No Matching Typologies"
            description="No behavioral patterns matched your search and filter criteria."
            action={
              <button
                onClick={() => {
                  setSearchQuery("")
                  setTypeFilter("all")
                }}
                className="px-3 py-1.5 text-xs font-mono rounded bg-panel border border-border hover:border-terminal-cyan text-foreground"
              >
                Reset Filters
              </button>
            }
          />
        )}

        {/* Typologies Grid */}
        {!loading && !errorMsg && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {filteredBehaviors.map((item) => {
              const riskPercent = Math.round(item.averageRisk * 100)
              const isSusp = isTypologySuspicious(item.key)
              return (
                <Panel key={item.key} className="hover:border-border/90 transition-all flex flex-col justify-between">
                  <div>
                    {/* Header */}
                    <PanelHeader
                      title={
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground text-sm">
                            {item.name}
                          </span>
                          <code className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/40 text-muted-foreground">
                            {item.key}
                          </code>
                        </div>
                      }
                      icon={
                        isSusp ? (
                          <AlertTriangle className="h-4 w-4 text-severity-high flex-shrink-0" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4 text-severity-low flex-shrink-0" />
                        )
                      }
                      action={
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase",
                            isSusp
                              ? "bg-severity-high/10 text-severity-high border-severity-high/30"
                              : "bg-severity-low/10 text-severity-low border-severity-low/30",
                          )}
                        >
                          {isSusp ? "Suspicious Pattern" : "Normal Flow"}
                        </span>
                      }
                    />

                    <PanelBody className="space-y-4">
                      {/* Description */}
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {item.description}
                      </p>

                      {/* Metric Bar Row */}
                      <div className="grid grid-cols-2 gap-2 p-2.5 bg-background border border-border/60 rounded font-mono">
                        <div>
                          <div className="text-[10px] text-muted-foreground uppercase">Occurrences</div>
                          <div className="text-sm font-bold text-foreground mt-0.5">
                            {formatNumber(item.count)}
                            <span className="text-[10px] font-normal text-muted-foreground ml-1">
                              ({item.percentage.toFixed(1)}%)
                            </span>
                          </div>
                        </div>

                        <div>
                          <div className="text-[10px] text-muted-foreground uppercase">Avg ML Risk</div>
                          <div
                            className="text-sm font-bold mt-0.5"
                            style={{ color: severityColorVar(item.averageRisk >= 0.7 ? "critical" : item.averageRisk >= 0.5 ? "high" : item.averageRisk >= 0.3 ? "medium" : "low") }}
                          >
                            {riskPercent}%
                          </div>
                        </div>
                      </div>

                      {/* Risk Meter & Severity Breakdown */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] font-mono">
                          <span className="text-muted-foreground">Severity Breakdown</span>
                          <div className="flex items-center gap-2">
                            {item.severityBreakdown.critical > 0 && (
                              <span className="text-[10px] text-severity-critical font-bold">
                                {item.severityBreakdown.critical} Crit
                              </span>
                            )}
                            {item.severityBreakdown.high > 0 && (
                              <span className="text-[10px] text-severity-high font-bold">
                                {item.severityBreakdown.high} High
                              </span>
                            )}
                            {item.severityBreakdown.medium > 0 && (
                              <span className="text-[10px] text-severity-medium font-bold">
                                {item.severityBreakdown.medium} Med
                              </span>
                            )}
                            {item.severityBreakdown.low > 0 && (
                              <span className="text-[10px] text-severity-low font-bold">
                                {item.severityBreakdown.low} Low
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="h-1.5 w-full bg-background rounded-full overflow-hidden flex">
                          {item.count > 0 && (
                            <>
                              <div
                                style={{ width: `${(item.severityBreakdown.critical / item.count) * 100}%` }}
                                className="bg-severity-critical h-full"
                              />
                              <div
                                style={{ width: `${(item.severityBreakdown.high / item.count) * 100}%` }}
                                className="bg-severity-high h-full"
                              />
                              <div
                                style={{ width: `${(item.severityBreakdown.medium / item.count) * 100}%` }}
                                className="bg-severity-medium h-full"
                              />
                              <div
                                style={{ width: `${(item.severityBreakdown.low / item.count) * 100}%` }}
                                className="bg-severity-low h-full"
                              />
                            </>
                          )}
                        </div>
                      </div>

                      {/* Sample Transactions */}
                      {item.topTransactions && item.topTransactions.length > 0 && (
                        <div className="space-y-2 pt-1 border-t border-border/50">
                          <div className="text-[10px] font-mono uppercase text-muted-foreground flex items-center justify-between">
                            <span>Top Transactions</span>
                            <span>TXID / Amount / Risk</span>
                          </div>
                          <div className="space-y-1">
                            {item.topTransactions.map((tx) => (
                              <div
                                key={tx.txid}
                                className="flex items-center justify-between p-1.5 rounded bg-background/60 hover:bg-background border border-border/40 text-xs font-mono transition-colors"
                              >
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => navigate(`/investigation/${tx.txid}?entityType=transaction`)}
                                    className="hover:underline flex items-center gap-1 text-foreground"
                                  >
                                    <MonoId value={tx.txid} head={6} tail={4} />
                                    <ExternalLink className="h-2.5 w-2.5 text-muted-foreground" />
                                  </button>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-muted-foreground">{formatBtc(tx.amount)}</span>
                                  <SeverityBadge severity={tx.severity} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </PanelBody>
                  </div>

                  {/* Actions Footer */}
                  <div className="p-3 bg-panel/50 border-t border-border flex items-center justify-between text-xs font-mono">
                    <button
                      onClick={() => navigate(`/transactions?behavior=${item.key}`)}
                      className="text-terminal-cyan hover:underline flex items-center gap-1"
                    >
                      View All {formatNumber(item.count)} Transactions
                      <ArrowRight className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => navigate(`/graph?filter=${item.key}`)}
                      className="text-muted-foreground hover:text-foreground flex items-center gap-1"
                    >
                      Inspect in Graph
                      <GitFork className="h-3 w-3" />
                    </button>
                  </div>
                </Panel>
              )
            })}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
