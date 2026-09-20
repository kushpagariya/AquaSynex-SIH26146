import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Bell,
  ShieldAlert,
  Waves,
  CircleCheck,
  Layers,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { StatCard } from "@/components/stat-card"
import { AnomalyOverview } from "@/components/anomaly-overview"
import { AlertTable } from "@/components/alert-table"
import { ErrorState, LoadingState } from "@/components/ui/states"
import { getAlerts, getDashboardStats, getBehaviorAnalytics } from "@/data/service"
import type { Alert, DashboardStats, BehaviorAnalyticsItem } from "@/data/types"
import { formatDateTime, formatNumber } from "@/lib/utils"

export function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[] | null>(null)
  const [behaviors, setBehaviors] = useState<BehaviorAnalyticsItem[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      getDashboardStats(),
      getAlerts(),
      getBehaviorAnalytics().catch(() => []),
    ])
      .then(([s, a, b]) => {
        setStats(s)
        setAlerts(a)
        setBehaviors(b)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to connect to TraceGrid backend")
      })
  }, [])

  const topBehaviors = behaviors.filter((b) => b.count > 0).slice(0, 4)

  return (
    <AppLayout title="Overview">
      {errorMsg ? (
        <ErrorState
          title="Backend Connection Error"
          description={errorMsg}
        />
      ) : !stats || !alerts ? (
        <LoadingState label="Loading system overview" />
      ) : (
        <div className="space-y-6">
          {stats.totalTransactions === 0 ? (
            <div className="flex items-center justify-between rounded-lg border border-line bg-panel p-5 shadow-xs">
              <div>
                <p className="text-sm font-semibold text-fg font-sans">No dataset loaded yet</p>
                <p className="mt-0.5 text-xs text-fg-muted font-sans">
                  Ingest a Bitcoin transaction dataset to run offline forensic risk attribution.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/dataset")}
                className="rounded border border-accent bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent/90 transition-colors"
              >
                Go to Datasets →
              </button>
            </div>
          ) : null}

          {/* TOP: 3 Clean Typography Metric Blocks (No baseline comparisons) */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard
              label="Transactions"
              value={stats.totalTransactions}
              sublabel="Total observed volume"
              icon={Activity}
              onClick={() => navigate("/transactions")}
            />
            <StatCard
              label="Active Alerts"
              value={stats.activeAlerts}
              sublabel="Prioritized investigation cases"
              icon={Bell}
              onClick={() => navigate("/alerts")}
            />
            <StatCard
              label="High-Risk Transactions"
              value={stats.highRiskEntities}
              sublabel="ML confidence score ≥ 70"
              icon={ShieldAlert}
              onClick={() => navigate("/alerts")}
            />
          </div>

          {/* MAIN ROW: Activity Chart on Left, Priority Investigation Queue on Right */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Left: Risk / Transaction Activity Chart */}
            <Panel className="lg:col-span-7 min-w-0">
              <PanelHeader
                title="Transaction & Risk Activity"
                subtitle="Temporal volume distribution with detected anomalies"
                icon={<Waves className="size-4" />}
                action={
                  <div className="flex items-center gap-4 text-xs text-fg-muted font-sans">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2.5 rounded-sm bg-[#CBD5E1]" />
                      Total Volume
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2.5 rounded-sm bg-[#A63D3D]" />
                      Anomalies
                    </span>
                  </div>
                }
              />
              <PanelBody className="min-w-0">
                <AnomalyOverview series={stats.anomalySeries} />
              </PanelBody>
            </Panel>

            {/* Right: Priority Investigation Queue */}
            <Panel className="lg:col-span-5 min-w-0 flex flex-col">
              <PanelHeader
                title="Priority Alert Queue"
                subtitle="Highest risk attribution cases"
                icon={<Bell className="size-4" />}
                action={
                  <button
                    type="button"
                    onClick={() => navigate("/alerts")}
                    className="text-xs font-semibold text-accent hover:underline font-sans"
                  >
                    View queue ({alerts.length}) →
                  </button>
                }
              />
              <div className="flex-1 overflow-x-auto">
                <AlertTable alerts={alerts.slice(0, 5)} compact={true} />
              </div>
            </Panel>
          </div>

          {/* BOTTOM ROW: Behavior Distribution + System Processing Status */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Bottom Left: Behavior Distribution */}
            <Panel className="lg:col-span-7 min-w-0">
              <PanelHeader
                title="Behavior Distribution"
                subtitle="Classified financial crime and transfer typologies"
                icon={<Layers className="size-4" />}
                action={
                  <button
                    type="button"
                    onClick={() => navigate("/behaviors")}
                    className="text-xs font-semibold text-accent hover:underline font-sans"
                  >
                    All typologies →
                  </button>
                }
              />
              <PanelBody className="space-y-4 font-sans">
                {topBehaviors.length > 0 ? (
                  <div className="space-y-3">
                    {topBehaviors.map((b) => (
                      <div
                        key={b.key}
                        onClick={() => navigate(`/transactions?behavior=${b.key}`)}
                        className="cursor-pointer rounded border border-line bg-panel-2 p-3 transition-colors hover:border-accent/40"
                      >
                        <div className="flex items-center justify-between text-xs font-medium">
                          <span className="font-semibold text-fg">
                            {b.name}
                          </span>
                          <span className="font-mono text-fg-muted font-medium tabular-nums">
                            {formatNumber(b.count)} txs ({b.percentage.toFixed(1)}%)
                          </span>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-panel border border-line-soft">
                          <div
                            className={`h-full rounded-full transition-all ${
                              b.key === "normal" || b.key === "benign_high_volume"
                                ? "bg-[#173B63]"
                                : "bg-[#A63D3D]"
                            }`}
                            style={{ width: `${Math.max(b.percentage, 4)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-fg-subtle">No behavior typologies classified yet.</p>
                )}
              </PanelBody>
            </Panel>

            {/* Bottom Right: System Processing Status */}
            <Panel className="lg:col-span-5 min-w-0 flex flex-col">
              <PanelHeader
                title="System Processing Status"
                subtitle="Dual-model ML pipeline operational state"
                icon={<CircleCheck className="size-4" />}
              />
              <PanelBody className="space-y-3 flex-1 flex flex-col justify-between font-sans">
                <div className="space-y-2.5">
                  <ProcessingRow
                    label="Ingestion & Parsing"
                    state={stats.processingStatus?.ingestion ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                    done={stats.processingStatus?.ingestion}
                  />
                  <ProcessingRow
                    label="Entity Resolution"
                    state={stats.processingStatus?.entityResolution ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                    done={stats.processingStatus?.entityResolution}
                  />
                  <ProcessingRow
                    label="Risk Scoring (XGBoost + CatBoost)"
                    state={stats.processingStatus?.riskScoring ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                    done={stats.processingStatus?.riskScoring}
                  />
                  <ProcessingRow
                    label="Graph Topology Build"
                    state={stats.processingStatus?.graphBuild ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                    done={stats.processingStatus?.graphBuild}
                  />
                </div>

                <div className="rounded border border-line bg-panel-2 p-3 text-xs">
                  <div className="flex items-center justify-between text-fg-muted">
                    <span className="text-[11px] font-medium">Last Processed</span>
                    <span className="font-mono text-[11px]">
                      {stats.lastProcessed ? formatDateTime(stats.lastProcessed) : "No run recorded"}
                    </span>
                  </div>
                  <div className="mt-2.5 pt-2 border-t border-line flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-fg-subtle uppercase font-semibold">Anomalies Detected</p>
                      <p className="mt-0.5 text-base font-bold text-[#A63D3D] tabular-nums font-mono">
                        {stats.anomaliesDetected}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-fg-subtle uppercase font-semibold">Suspicious Ratio</p>
                      <p className="mt-0.5 text-base font-bold text-accent tabular-nums font-mono">
                        {stats.totalTransactions > 0
                          ? `${((stats.anomaliesDetected / stats.totalTransactions) * 100).toFixed(1)}%`
                          : "0.0%"}
                      </p>
                    </div>
                  </div>
                </div>
              </PanelBody>
            </Panel>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

function ProcessingRow({
  label,
  state,
  done,
}: {
  label: string
  state: string
  done?: boolean
}) {
  return (
    <div className="flex items-center justify-between text-xs py-0.5">
      <span className="text-fg-muted font-sans font-medium">{label}</span>
      <span className="flex items-center gap-1.5 font-medium">
        <span
          className={
            done ? "size-1.5 rounded-full bg-[#2F6B4F]" : "size-1.5 rounded-full bg-[#A46A16]"
          }
        />
        <span className={done ? "text-[#2F6B4F]" : "text-[#A46A16]"}>{state}</span>
      </span>
    </div>
  )
}
