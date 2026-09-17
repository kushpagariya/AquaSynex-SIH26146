import { useEffect, useState } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import {
  ShieldAlert,
  ListTree,
  Info,
  Network,
  Clock,
  ArrowLeftRight,
  FileSearch,
  Share2,
  X,
  GitFork,
  Users,
  Activity,
  Bell,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import {
  EntityTypeBadge,
  SeverityBadge,
  severityColorVar,
} from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { RiskFactors } from "@/components/investigation/risk-factors"
import {
  EntityInfo,
  NetworkInfoPanel,
} from "@/components/investigation/entity-info"
import { Timeline } from "@/components/investigation/timeline"
import { EvidencePanel } from "@/components/investigation/evidence-panel"
import {
  GraphViewer,
  type GraphSelection,
} from "@/components/investigation/graph-viewer"
import { TransactionTable } from "@/components/transaction-table"
import { getInvestigation, getAlerts } from "@/data/service"
import type { Investigation, EntityType } from "@/data/types"

export function InvestigationPage() {
  const { entityId } = useParams<{ entityId: string }>()
  const [searchParams] = useSearchParams()
  const entityTypeParam = searchParams.get("entityType") || searchParams.get("type") || undefined
  const navigate = useNavigate()
  const [data, setData] = useState<Investigation | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [selection, setSelection] = useState<GraphSelection | null>(null)

  useEffect(() => {
    if (!entityId) {
      setData(null)
      setNotFound(false)
      setErrorMsg(null)
      setSelection(null)
      getAlerts()
        .then((alerts) => {
          if (alerts && alerts.length > 0) {
            navigate(`/investigation/${alerts[0].entityId}?entityType=${alerts[0].entityType}`, {
              replace: true,
            })
          }
        })
        .catch(() => {})
      return
    }
    setData(null)
    setNotFound(false)
    setErrorMsg(null)
    setSelection(null)
    getInvestigation(entityId, entityTypeParam)
      .then((res) => {
        if (res) setData(res)
        else setNotFound(true)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load investigation")
      })
  }, [entityId, entityTypeParam, navigate])

  return (
    <AppLayout title="Case Investigation">
      {errorMsg ? (
        <ErrorState
          title="Failed to load investigation"
          description={errorMsg}
        />
      ) : notFound ? (
        <ErrorState
          title="Entity not found"
          description="This entity is not present in the loaded dataset."
        />
      ) : !entityId ? (
        <EmptyState
          title="No entity selected for investigation"
          description="Select a flagged entity or address from the Dashboard or Alerts view, or search for a Bitcoin address above."
        />
      ) : !data ? (
        <LoadingState label="Building forensic case dossier" />
      ) : (
        <div className="space-y-6 font-sans">
          {/* Top: Restrained Institutional Risk Header */}
          <Panel>
            <PanelBody className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between p-6">
              <div className="flex items-start gap-6">
                {/* Restrained Typography-Driven Risk Block */}
                <div className="flex flex-col items-center justify-center rounded border border-line bg-panel-2 px-5 py-3.5 min-w-[110px] text-center">
                  <span
                    className="font-mono text-3xl font-bold tabular-nums"
                    style={{ color: severityColorVar(data.entity.risk.severity) }}
                  >
                    {data.entity.risk.score}
                  </span>
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider mt-1"
                    style={{ color: severityColorVar(data.entity.risk.severity) }}
                  >
                    {data.entity.risk.severity} Risk
                  </span>
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-bold text-fg">
                      {data.entity.label}
                    </h2>
                    <EntityTypeBadge type={data.entity.type} />
                    <SeverityBadge severity={data.entity.risk.severity} />
                  </div>

                  {data.entity.address ? (
                    <div className="mt-1.5">
                      <MonoId value={data.entity.address} head={18} tail={12} className="text-xs" />
                    </div>
                  ) : (
                    <div className="mt-1.5">
                      <MonoId value={data.entity.id} head={18} tail={12} className="text-xs" />
                    </div>
                  )}

                  <p className="mt-2 text-xs text-fg-muted flex items-center gap-2 font-sans">
                    <span>
                      Attribution:{" "}
                      <strong className="text-fg font-semibold">
                        {data.entity.tags.length ? data.entity.tags.join(", ") : "Observed Activity"}
                      </strong>
                    </span>
                    <span className="text-[11px] text-fg-subtle">
                      {data.entity.type !== "transaction"
                        ? "(Aggregate ML Risk from Associated Transactions)"
                        : "(Transaction-Level ML Prediction)"}
                    </span>
                  </p>
                </div>
              </div>

              {/* Investigation Quick Action Toolbar */}
              <div className="flex flex-wrap items-center gap-2 self-start lg:self-center">
                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      `/graph?focus=${encodeURIComponent(data.entity.address || data.entity.id)}`,
                    )
                  }
                  className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 transition-colors"
                >
                  <GitFork className="size-3.5 text-accent" />
                  Graph Explorer
                </button>
                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      `/entities?focus=${encodeURIComponent(data.entity.address || data.entity.id)}`,
                    )
                  }
                  className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 transition-colors"
                >
                  <Users className="size-3.5 text-accent" />
                  Inferred Cluster
                </button>
                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      `/transactions?txid=${encodeURIComponent(data.entity.address || data.entity.id)}`,
                    )
                  }
                  className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 transition-colors"
                >
                  <Activity className="size-3.5 text-accent" />
                  Transactions
                </button>
                <button
                  type="button"
                  onClick={() =>
                    navigate(
                      `/alerts?search=${encodeURIComponent(data.entity.address || data.entity.id)}`,
                    )
                  }
                  className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 transition-colors"
                >
                  <Bell className="size-3.5 text-[#A63D3D]" />
                  Alerts
                </button>
              </div>
            </PanelBody>
          </Panel>

          {/* Main Content: Two-Column Layout (LEFT: Why is it suspicious / SHAP, RIGHT: Entity/Transaction Info) */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* LEFT: Top model contributors / SHAP factors */}
            <Panel>
              <PanelHeader
                title="Top model contributors for this transaction"
                subtitle="TreeSHAP feature impact on predicted risk score"
                icon={<ShieldAlert className="size-4" />}
              />
              <PanelBody>
                <RiskFactors risk={data.entity.risk} />
              </PanelBody>
            </Panel>

            {/* RIGHT: Entity / Transaction Information */}
            <Panel>
              <PanelHeader
                title="Entity Telemetry Dossier"
                subtitle="Aggregated on-chain profile and historical activity"
                icon={<Info className="size-4" />}
              />
              <PanelBody>
                <EntityInfo entity={data.entity} />
              </PanelBody>
            </Panel>
          </div>

          {/* Relationship Graph */}
          <Panel>
            <PanelHeader
              title="Topological Relationship Graph"
              subtitle="Interactive bipartite subgraph around the investigated entity"
              icon={<Share2 className="size-4" />}
              action={<GraphLegend />}
            />
            <div className="relative h-[440px]">
              <GraphViewer data={data.graph} onSelect={setSelection} />
              {selection ? (
                <NodeDetails
                  selection={selection}
                  onClose={() => setSelection(null)}
                  onOpen={(id, type) => navigate(`/investigation/${id}?entityType=${type}`)}
                />
              ) : null}
            </div>
          </Panel>

          {/* Timeline + Network Information */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Activity Chronology"
                subtitle="Observed transaction sequence and anomalous events"
                icon={<Clock className="size-4" />}
              />
              <PanelBody>
                <Timeline events={data.timeline} />
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader
                title="Network Peer Telemetry"
                subtitle="P2P broadcast metadata recorded at announcement"
                icon={<Network className="size-4" />}
              />
              <PanelBody>
                <NetworkInfoPanel entity={data.entity} />
              </PanelBody>
            </Panel>
          </div>

          {/* Connected Entities + Related Transactions */}
          <Panel>
            <PanelHeader
              title="Connected Counterparties"
              subtitle={`${data.connectedEntities.length} direct topological relationships`}
              icon={<ListTree className="size-4" />}
            />
            <div className="grid grid-cols-1 divide-y divide-line-soft sm:grid-cols-2 sm:divide-y-0 sm:[&>*:nth-child(odd)]:border-r sm:[&>*]:border-line-soft">
              {data.connectedEntities.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => navigate(`/investigation/${c.id}?entityType=${c.type}`)}
                  className="flex items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-accent-soft/30"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="size-2 rounded-full"
                      style={{ backgroundColor: severityColorVar(c.risk.severity) }}
                    />
                    <span className="text-xs font-semibold text-fg font-mono">{c.label}</span>
                    <EntityTypeBadge type={c.type} />
                  </div>
                  <span
                    className="font-mono text-xs font-bold tabular-nums"
                    style={{ color: severityColorVar(c.risk.severity) }}
                  >
                    {c.risk.score}
                  </span>
                </button>
              ))}
            </div>
          </Panel>

          {/* Transactions */}
          <Panel>
            <PanelHeader
              title="Associated Transactions"
              subtitle={`${data.transactions.length} transactions connected to this case`}
              icon={<ArrowLeftRight className="size-4" />}
            />
            <TransactionTable transactions={data.transactions} />
          </Panel>

          {/* Evidence / Explanation */}
          <Panel>
            <PanelHeader
              title="Evidence & Grounded Findings"
              subtitle="Attributed forensic rationale behind ML risk scoring"
              icon={<FileSearch className="size-4" />}
            />
            <EvidencePanel items={data.evidence} />
          </Panel>
        </div>
      )}
    </AppLayout>
  )
}

function GraphLegend() {
  const items = [
    { label: "Wallet", color: "#475569" },
    { label: "Transaction", color: "#173B63" },
    { label: "IP", color: "#A46A16" },
    { label: "Mixer", color: "#A63D3D" },
    { label: "Exchange", color: "#2F6B4F" },
  ]
  return (
    <div className="hidden items-center gap-4 text-[11px] text-fg-muted md:flex font-sans">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5">
          <span
            className="size-2 rounded-full"
            style={{ backgroundColor: i.color }}
          />
          {i.label}
        </span>
      ))}
    </div>
  )
}

function NodeDetails({
  selection,
  onClose,
  onOpen,
}: {
  selection: GraphSelection
  onClose: () => void
  onOpen: (id: string, type: EntityType) => void
}) {
  const isEntity = selection.type !== "transaction"
  return (
    <div className="absolute right-3 top-3 w-64 rounded border border-line bg-panel p-4 shadow-lg font-sans">
      <div className="flex items-start justify-between gap-2 border-b border-line pb-2">
        <div className="min-w-0">
          <p className="truncate text-xs font-bold text-fg font-mono">
            {selection.label}
          </p>
          <div className="mt-1 flex items-center gap-1.5">
            <EntityTypeBadge type={selection.type} />
            {selection.severity ? (
              <SeverityBadge severity={selection.severity} />
            ) : null}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close node details"
          className="text-fg-subtle hover:text-fg"
        >
          <X className="size-3.5" />
        </button>
      </div>
      <p className="mt-2.5 text-xs text-fg-muted font-sans">
        {selection.neighbors} direct connection
        {selection.neighbors === 1 ? "" : "s"}
      </p>
      <button
        type="button"
        onClick={() => onOpen(selection.id, selection.type)}
        className="mt-3 w-full rounded border border-accent bg-accent py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors font-sans"
      >
        {isEntity ? "Investigate entity →" : "Investigate transaction →"}
      </button>
    </div>
  )
}
