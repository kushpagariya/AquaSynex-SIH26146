import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Users,
  Bell,
  ShieldAlert,
  Waves,
  CircleCheck,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { StatCard } from "@/components/stat-card"
import { AnomalyOverview } from "@/components/anomaly-overview"
import { AlertTable } from "@/components/alert-table"
import { ErrorState, LoadingState } from "@/components/ui/states"
import { getAlerts, getDashboardStats } from "@/data/service"
import type { Alert, DashboardStats } from "@/data/types"
import { formatDateTime } from "@/lib/utils"

export function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [alerts, setAlerts] = useState<Alert[] | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getDashboardStats(), getAlerts()])
      .then(([s, a]) => {
        setStats(s)
        setAlerts(a)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to connect to AquaSynex backend")
      })
  }, [])

  return (
    <AppLayout title="Dashboard">
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
            <div className="flex items-center justify-between rounded-lg border border-line bg-panel p-4">
              <div>
                <p className="text-sm font-semibold text-fg">No dataset loaded yet</p>
                <p className="mt-0.5 text-xs text-fg-muted">
                  Ingest a Bitcoin transaction dataset (CSV, JSON, Parquet) to run offline ML anomaly detection.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/dataset")}
                className="rounded border border-accent/40 bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/10"
              >
                Go to Datasets →
              </button>
            </div>
          ) : null}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Transactions"
              value={stats.totalTransactions}
              delta={stats.deltas.transactions}
              icon={Activity}
              onClick={() => navigate("/dataset")}
            />
            <StatCard
              label="Entities"
              value={stats.totalEntities}
              delta={stats.deltas.entities}
              icon={Users}
              onClick={() => navigate("/investigation")}
            />
            <StatCard
              label="Active Alerts"
              value={stats.activeAlerts}
              delta={stats.deltas.alerts}
              icon={Bell}
              accent="high"
              onClick={() => navigate("/alerts")}
            />
            <StatCard
              label="High Risk"
              value={stats.highRiskEntities}
              delta={stats.deltas.highRisk}
              icon={ShieldAlert}
              accent="critical"
              onClick={() => navigate("/alerts")}
            />
          </div>

          <Panel className="min-w-0">
            <PanelHeader
              title="Anomaly / Risk Overview"
              subtitle="Hourly transaction volume with detected anomalies"
              icon={<Waves className="size-4" />}
              action={
                <div className="flex items-center gap-4 text-xs text-fg-subtle">
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-panel-2" />
                    Transactions
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-risk-high/70" />
                    Anomalies
                  </span>
                </div>
              }
            />
            <PanelBody className="min-w-0">
              <AnomalyOverview series={stats.anomalySeries} />
            </PanelBody>
          </Panel>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <Panel className="min-w-0 xl:col-span-2">
              <PanelHeader
                title="Recent Suspicious Activity"
                subtitle="Highest-priority alerts in the queue"
                icon={<Bell className="size-4" />}
                action={
                  <button
                    type="button"
                    onClick={() => navigate("/alerts")}
                    className="text-xs font-medium text-accent hover:underline"
                  >
                    View all
                  </button>
                }
              />
              <AlertTable alerts={alerts.slice(0, 5)} compact />
            </Panel>

            <Panel className="min-w-0">
              <PanelHeader
                title="Processing Status"
                icon={<CircleCheck className="size-4" />}
              />
              <PanelBody className="space-y-4">
                <ProcessingRow
                  label="Ingestion"
                  state={stats.processingStatus?.ingestion ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                  done={stats.processingStatus?.ingestion}
                />
                <ProcessingRow
                  label="Entity resolution"
                  state={stats.processingStatus?.entityResolution ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                  done={stats.processingStatus?.entityResolution}
                />
                <ProcessingRow
                  label="Risk scoring"
                  state={stats.processingStatus?.riskScoring ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                  done={stats.processingStatus?.riskScoring}
                />
                <ProcessingRow
                  label="Graph build"
                  state={stats.processingStatus?.graphBuild ? "Completed" : stats.totalTransactions > 0 ? "In progress" : "Idle"}
                  done={stats.processingStatus?.graphBuild}
                />
                <div className="rounded-md border border-line bg-panel-2 p-3">
                  <p className="text-xs text-fg-subtle">Last processed</p>
                  <p className="mt-0.5 font-mono-id text-sm text-fg">
                    {stats.lastProcessed ? formatDateTime(stats.lastProcessed) : "No dataset processed yet"}
                  </p>
                  <p className="mt-2 text-xs text-fg-subtle">Anomalies detected</p>
                  <p className="mt-0.5 font-mono-id text-sm text-risk-high">
                    {stats.anomaliesDetected}
                  </p>
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
    <div className="flex items-center justify-between">
      <span className="text-sm text-fg-muted">{label}</span>
      <span className="flex items-center gap-1.5 text-xs">
        <span
          className={
            done ? "size-1.5 rounded-full bg-risk-low" : "size-1.5 rounded-full bg-risk-medium"
          }
        />
        <span className={done ? "text-risk-low" : "text-risk-medium"}>{state}</span>
      </span>
    </div>
  )
}
