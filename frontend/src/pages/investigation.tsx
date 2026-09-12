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
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import {
  EntityTypeBadge,
  RiskScore,
  SeverityBadge,
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
import { severityColorVar } from "@/components/ui/badges"

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
        .catch(() => {
          // Stay in clean empty state
        })
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
    <AppLayout title="Investigation">
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
        <LoadingState label="Building investigation" />
      ) : (
        <div className="space-y-6">
          {/* Entity + Risk header */}
          <Panel>
            <PanelBody className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-5">
                <RiskScore
                  score={data.entity.risk.score}
                  severity={data.entity.risk.severity}
                  size="lg"
                />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-semibold text-fg">
                      {data.entity.label}
                    </h2>
                    <EntityTypeBadge type={data.entity.type} />
                    <SeverityBadge severity={data.entity.risk.severity} />
                  </div>
                  {data.entity.address ? (
                    <div className="mt-1.5">
                      <MonoId value={data.entity.address} head={14} tail={10} />
                    </div>
                  ) : null}
                  <p
                    className="mt-2 text-xs font-medium uppercase tracking-wide"
                    style={{
                      color: severityColorVar(data.entity.risk.severity),
                    }}
                  >
                    {data.entity.risk.score} / 100 —{" "}
                    {data.entity.risk.severity} risk
                  </p>
                </div>
              </div>
            </PanelBody>
          </Panel>

          {/* Risk factors + entity info */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Why is it suspicious?"
                subtitle="ML contributing factors"
                icon={<ShieldAlert className="size-4" />}
              />
              <PanelBody>
                <RiskFactors risk={data.entity.risk} />
              </PanelBody>
            </Panel>
            <Panel>
              <PanelHeader
                title="Entity Information"
                icon={<Info className="size-4" />}
              />
              <PanelBody>
                <EntityInfo entity={data.entity} />
              </PanelBody>
            </Panel>
          </div>

          {/* Relationship graph */}
          <Panel>
            <PanelHeader
              title="Relationship Graph"
              subtitle="Select a node to highlight its neighborhood"
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

          {/* Timeline + network */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Timeline"
                subtitle="Suspicious activity in chronological order"
                icon={<Clock className="size-4" />}
              />
              <PanelBody>
                <Timeline events={data.timeline} />
              </PanelBody>
            </Panel>
            <Panel>
              <PanelHeader
                title="Network Information"
                icon={<Network className="size-4" />}
              />
              <PanelBody>
                <NetworkInfoPanel entity={data.entity} />
              </PanelBody>
            </Panel>
          </div>

          {/* Connected entities */}
          <Panel>
            <PanelHeader
              title="Connected Entities"
              subtitle={`${data.connectedEntities.length} direct connections`}
              icon={<ListTree className="size-4" />}
            />
            <div className="grid grid-cols-1 divide-y divide-line-soft sm:grid-cols-2 sm:divide-y-0 sm:[&>*:nth-child(odd)]:border-r sm:[&>*]:border-line-soft">
              {data.connectedEntities.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => navigate(`/investigation/${c.id}?entityType=${c.type}`)}
                  className="flex items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-panel-2"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="size-2 rounded-full"
                      style={{ backgroundColor: severityColorVar(c.risk.severity) }}
                    />
                    <span className="text-sm font-medium text-fg">{c.label}</span>
                    <EntityTypeBadge type={c.type} />
                  </div>
                  <span
                    className="font-mono-id text-sm font-semibold tabular-nums"
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
              title="Transactions"
              subtitle={`${data.transactions.length} related transactions`}
              icon={<ArrowLeftRight className="size-4" />}
            />
            <TransactionTable transactions={data.transactions} />
          </Panel>

          {/* Evidence */}
          <Panel>
            <PanelHeader
              title="Evidence / Explanation"
              subtitle="Grounded rationale behind the flag"
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
    { label: "Wallet", color: "#38bdf8" },
    { label: "Transaction", color: "#a78bfa" },
    { label: "IP", color: "#f59e0b" },
    { label: "Mixer", color: "#ef4444" },
    { label: "Exchange", color: "#22c55e" },
  ]
  return (
    <div className="hidden items-center gap-3 text-[11px] text-fg-subtle md:flex">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-full"
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
    <div className="absolute right-3 top-3 w-60 rounded-md border border-line bg-panel/95 p-3 shadow-xl shadow-black/40 backdrop-blur">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-fg">
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
          <X className="size-4" />
        </button>
      </div>
      <p className="mt-3 text-xs text-fg-subtle">
        {selection.neighbors} direct connection
        {selection.neighbors === 1 ? "" : "s"}
      </p>
      <button
        type="button"
        onClick={() => onOpen(selection.id, selection.type)}
        className="mt-3 w-full rounded border border-accent/40 bg-accent-soft py-1.5 text-xs font-medium text-accent hover:bg-accent/10"
      >
        {isEntity ? "Investigate this entity →" : "Investigate transaction →"}
      </button>
    </div>
  )
}
