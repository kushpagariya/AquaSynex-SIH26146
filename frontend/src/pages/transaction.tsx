import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Receipt,
  Network,
  Boxes,
  ArrowLeftRight,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState } from "@/components/ui/states"
import { getTransaction } from "@/data/service"
import { entityById } from "@/data/mock"
import type { Transaction, TxIO } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber } from "@/lib/utils"

export function TransactionPage() {
  const { txid } = useParams<{ txid: string }>()
  const navigate = useNavigate()
  const [tx, setTx] = useState<Transaction | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!txid) return
    setTx(null)
    setNotFound(false)
    getTransaction(txid).then((res) => {
      if (res) setTx(res)
      else setNotFound(true)
    })
  }, [txid])

  return (
    <AppLayout title="Transaction">
      {notFound ? (
        <ErrorState
          title="Transaction not found"
          description="This TXID is not present in the loaded dataset."
        />
      ) : !tx ? (
        <LoadingState label="Loading transaction" />
      ) : (
        <div className="space-y-6">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-sm text-fg-muted hover:text-accent"
          >
            <ArrowLeft className="size-4" />
            Back
          </button>

          {/* Overview */}
          <Panel>
            <PanelHeader
              title="Transaction Overview"
              icon={<Receipt className="size-4" />}
              action={
                tx.severity ? (
                  <div className="flex items-center gap-2">
                    <span
                      className="font-mono-id text-sm font-semibold tabular-nums"
                      style={{ color: severityColorVar(tx.severity) }}
                    >
                      {tx.riskScore}
                    </span>
                    <SeverityBadge severity={tx.severity} />
                  </div>
                ) : null
              }
            />
            <PanelBody className="space-y-4">
              <div>
                <p className="text-xs text-fg-subtle">TXID</p>
                <MonoId value={tx.txid} truncate={false} className="mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Metric label="Amount" value={formatBtc(tx.amount)} accent />
                <Metric label="Fee" value={`${tx.fee.toFixed(5)} BTC`} />
                <Metric label="Block" value={formatNumber(tx.block)} />
                <Metric label="Confirmations" value={String(tx.confirmations)} />
              </div>
              <div>
                <p className="text-xs text-fg-subtle">Timestamp</p>
                <p className="mt-1 font-mono-id text-sm text-fg">
                  {formatDateTime(tx.timestamp)}
                </p>
              </div>
            </PanelBody>
          </Panel>

          {/* Inputs / Outputs */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title={`Inputs (${tx.inputs.length})`}
                icon={<ArrowRight className="size-4" />}
              />
              <IoList io={tx.inputs} onOpen={(id) => navigate(`/investigation/${id}`)} />
            </Panel>
            <Panel>
              <PanelHeader
                title={`Outputs (${tx.outputs.length})`}
                icon={<ArrowLeft className="size-4" />}
              />
              <IoList io={tx.outputs} onOpen={(id) => navigate(`/investigation/${id}`)} />
            </Panel>
          </div>

          {/* Network + related */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Network Metadata"
                icon={<Network className="size-4" />}
              />
              <PanelBody>
                <dl className="divide-y divide-line-soft">
                  <NetRow label="IP address">
                    <MonoId value={tx.network.ip} truncate={false} />
                  </NetRow>
                  <NetRow label="Port">
                    <span className="font-mono-id tabular-nums">
                      {tx.network.port}
                    </span>
                  </NetRow>
                  <NetRow label="ASN">
                    <span className="font-mono-id">{tx.network.asn}</span>
                  </NetRow>
                  <NetRow label="Organization">{tx.network.asnOrg}</NetRow>
                  <NetRow label="Country">
                    {tx.network.country} ({tx.network.countryCode})
                  </NetRow>
                </dl>
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader
                title="Related Entities"
                subtitle={`${tx.relatedEntityIds.length} entities`}
                icon={<ArrowLeftRight className="size-4" />}
              />
              <div className="divide-y divide-line-soft">
                {tx.relatedEntityIds.map((id) => {
                  const e = entityById(id)
                  if (!e) return null
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => navigate(`/investigation/${id}`)}
                      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-panel-2"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="size-2 rounded-full"
                          style={{
                            backgroundColor: severityColorVar(e.risk.severity),
                          }}
                        />
                        <span className="text-sm font-medium text-fg">
                          {e.label}
                        </span>
                      </div>
                      <span
                        className="font-mono-id text-sm font-semibold tabular-nums"
                        style={{ color: severityColorVar(e.risk.severity) }}
                      >
                        {e.risk.score}
                      </span>
                    </button>
                  )
                })}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: boolean
}) {
  return (
    <div className="rounded-md border border-line bg-panel-2 p-3">
      <p className="text-xs text-fg-subtle">{label}</p>
      <p
        className={
          "mt-1 font-mono-id text-sm font-semibold tabular-nums " +
          (accent ? "text-accent" : "text-fg")
        }
      >
        {value}
      </p>
    </div>
  )
}

function NetRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className="text-right text-sm text-fg">{children}</dd>
    </div>
  )
}

function IoList({
  io,
  onOpen,
}: {
  io: TxIO[]
  onOpen: (id: string) => void
}) {
  return (
    <ul className="divide-y divide-line-soft">
      {io.map((entry, i) => (
        <li
          key={`${entry.address}-${i}`}
          className="flex items-center justify-between gap-3 px-4 py-3"
        >
          <div className="min-w-0">
            {entry.entityId ? (
              <button
                type="button"
                onClick={() => onOpen(entry.entityId!)}
                className="font-mono-id text-sm text-accent hover:underline"
                title={entry.address}
              >
                {entry.address.slice(0, 16)}…
              </button>
            ) : (
              <span className="font-mono-id text-sm text-fg-muted">
                {entry.address.slice(0, 16)}…
              </span>
            )}
          </div>
          <span className="shrink-0 font-mono-id text-sm tabular-nums text-fg">
            {formatBtc(entry.amount)}
          </span>
        </li>
      ))}
    </ul>
  )
}
