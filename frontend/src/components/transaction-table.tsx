import { useNavigate } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import type { Transaction } from "@/data/types"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { formatBtc, formatTime } from "@/lib/utils"

export function TransactionTable({
  transactions,
}: {
  transactions: Transaction[]
}) {
  const navigate = useNavigate()

  if (!transactions.length) {
    return (
      <p className="px-5 py-8 text-center text-xs text-fg-subtle">
        No transactions associated with this entity.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
            <th className="px-5 py-3 font-sans">TXID</th>
            <th className="px-4 py-3 font-sans">Time</th>
            <th className="px-4 py-3 font-sans">Amount</th>
            <th className="px-4 py-3 font-sans">Fee (BTC)</th>
            <th className="px-4 py-3 font-sans">Risk</th>
            <th className="px-4 py-3 text-right font-sans">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line-soft text-xs">
          {transactions.map((t) => (
            <tr
              key={t.txid}
              onClick={() => navigate(`/transaction/${t.txid}`)}
              className="group cursor-pointer transition-colors hover:bg-accent-soft/30"
            >
              <td className="px-5 py-3.5">
                <MonoId value={t.txid} head={10} tail={6} copyable={false} />
              </td>
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-[11px] text-fg-subtle">
                {formatTime(t.timestamp)}
              </td>
              <td className="whitespace-nowrap px-4 py-3.5 font-sans font-semibold tabular-nums text-fg">
                {formatBtc(t.amount)}
              </td>
              <td className="whitespace-nowrap px-4 py-3.5 font-mono text-xs tabular-nums text-fg-muted">
                {t.fee.toFixed(5)}
              </td>
              <td className="px-4 py-3.5">
                {t.severity ? (
                  <div className="flex items-center gap-2">
                    <span
                      className="font-mono text-xs font-bold tabular-nums"
                      style={{ color: severityColorVar(t.severity) }}
                    >
                      {t.riskScore}
                    </span>
                    <SeverityBadge severity={t.severity} />
                  </div>
                ) : (
                  <span className="text-fg-subtle text-xs">—</span>
                )}
              </td>
              <td className="px-4 py-3.5 text-right">
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent opacity-70 group-hover:opacity-100 transition-opacity">
                  Inspect <ChevronRight className="size-3.5" />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
