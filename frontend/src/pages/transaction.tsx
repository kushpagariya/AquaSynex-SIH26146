import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Receipt,
  Network,
  ArrowLeftRight,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState } from "@/components/ui/states"
import { getTransaction } from "@/data/service"
import type { Transaction, TxIO } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber } from "@/lib/utils"

export function TransactionPage() {
  const { txid } = useParams<{ txid: string }>()
  const navigate = useNavigate()
  const [tx, setTx] = useState<Transaction | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!txid) return
    setTx(null)
    setNotFound(false)
    setErrorMsg(null)
    getTransaction(txid)
      .then((res) => {
        if (res) setTx(res)
        else setNotFound(true)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load transaction")
      })
  }, [txid])

  return (
    <AppLayout title="Transaction Record">
      {errorMsg ? (
        <ErrorState
          title="Failed to load transaction"
          description={errorMsg}
        />
      ) : notFound ? (
        <ErrorState
          title="Transaction not found"
          description="This TXID is not present in the loaded dataset."
        />
      ) : !tx ? (
        <LoadingState label="Loading transaction telemetry" />
      ) : (
        <div className="space-y-6">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline font-sans"
          >
            <ArrowLeft className="size-3.5" />
            Back to Transactions
          </button>

          {/* Overview */}
          <Panel>
            <PanelHeader
              title="Transaction Overview"
              subtitle="Cryptographic verification and blockchain metrics"
              icon={<Receipt className="size-4" />}
              action={
                tx.severity ? (
                  <div className="flex items-center gap-2">
                    <span
                      className="font-mono text-xs font-bold tabular-nums"
                      style={{ color: severityColorVar(tx.severity) }}
                    >
                      {tx.riskScore}
                    </span>
                    <SeverityBadge severity={tx.severity} />
                  </div>
                ) : null
              }
            />
            <PanelBody className="space-y-5">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans">TXID Hash</p>
                <MonoId value={tx.txid} truncate={false} className="mt-1 text-xs" />
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 font-sans">
                <Metric label="Amount" value={formatBtc(tx.amount)} accent />
                <Metric label="Fee" value={`${tx.fee.toFixed(5)} BTC`} />
                <Metric label="Block Height" value={formatNumber(tx.block)} />
                <Metric label="Confirmations" value={String(tx.confirmations)} />
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans">Timestamp</p>
                <p className="mt-1 font-mono text-xs text-fg">
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
                title="Network Peer Telemetry"
                icon={<Network className="size-4" />}
              />
              <PanelBody>
                <dl className="divide-y divide-line-soft font-sans text-xs">
                  <NetRow label="Broadcast Peer IP">
                    <MonoId value={tx.network.ip} truncate={false} />
                  </NetRow>
                  <NetRow label="Port">
                    <span className="font-mono tabular-nums">{tx.network.port}</span>
                  </NetRow>
                  <NetRow label="ASN">
                    <span className="font-mono">{tx.network.asn}</span>
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
                title="Connected Entities"
                subtitle={`${tx.relatedEntityIds.length} addresses observed`}
                icon={<ArrowLeftRight className="size-4" />}
              />
              <div className="divide-y divide-line-soft">
                {tx.relatedEntityIds.length === 0 ? (
                  <p className="px-5 py-6 text-xs text-fg-subtle">
                    No related entity addresses identified for this transaction.
                  </p>
                ) : (
                  tx.relatedEntityIds.map((id) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => navigate(`/investigation/${id}`)}
                      className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-accent-soft/30"
                    >
                      <div className="flex items-center gap-2">
                        <span className="size-1.5 rounded-full bg-accent" />
                        <span className="font-mono text-xs text-fg">
                          {id.length > 24 ? `${id.slice(0, 12)}…${id.slice(-8)}` : id}
                        </span>
                      </div>
                      <span className="text-xs font-medium text-accent hover:underline font-sans">
                        Investigate →
                      </span>
                    </button>
                  ))
                )}
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
    <div className="rounded border border-line bg-panel-2 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle font-sans">{label}</p>
      <p
        className={
          "mt-1 font-sans text-base font-bold tabular-nums " +
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
    <div className="flex items-center justify-between gap-3 py-2.5">
      <dt className="text-xs text-fg-muted font-medium">{label}</dt>
      <dd className="text-right text-xs text-fg">{children}</dd>
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
    <ul className="divide-y divide-line-soft text-xs">
      {io.map((entry, i) => (
        <li
          key={`${entry.address}-${i}`}
          className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-accent-soft/20 transition-colors"
        >
          <div className="min-w-0">
            {entry.entityId ? (
              <button
                type="button"
                onClick={() => onOpen(entry.entityId!)}
                className="font-mono text-xs text-accent hover:underline"
                title={entry.address}
              >
                {entry.address.slice(0, 16)}…
              </button>
            ) : (
              <span className="font-mono text-xs text-fg-muted">
                {entry.address.slice(0, 16)}…
              </span>
            )}
          </div>
          <span className="shrink-0 font-sans font-semibold tabular-nums text-fg">
            {formatBtc(entry.amount)}
          </span>
        </li>
      ))}
    </ul>
  )
}
