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
      <p className="px-4 py-6 text-sm text-fg-subtle">
        No transactions associated with this entity.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-fg-subtle">
            <th className="px-4 py-2.5 font-medium">TXID</th>
            <th className="px-4 py-2.5 font-medium">Time</th>
            <th className="px-4 py-2.5 font-medium">Amount</th>
            <th className="px-4 py-2.5 font-medium">Fee</th>
            <th className="px-4 py-2.5 font-medium">Risk</th>
            <th className="px-4 py-2.5" />
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr
              key={t.txid}
              onClick={() => navigate(`/transaction/${t.txid}`)}
              className="group cursor-pointer border-b border-line-soft transition-colors last:border-0 hover:bg-panel-2"
            >
              <td className="px-4 py-3">
                <MonoId value={t.txid} head={10} tail={6} copyable={false} />
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs text-fg-subtle">
                {formatTime(t.timestamp)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-mono-id tabular-nums text-fg">
                {formatBtc(t.amount)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs tabular-nums text-fg-subtle">
                {t.fee.toFixed(5)}
              </td>
              <td className="px-4 py-3">
                {t.severity ? (
                  <div className="flex items-center gap-2">
                    <span
                      className="font-mono-id text-xs font-semibold tabular-nums"
                      style={{ color: severityColorVar(t.severity) }}
                    >
                      {t.riskScore}
                    </span>
                    <SeverityBadge severity={t.severity} />
                  </div>
                ) : (
                  <span className="text-fg-subtle">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                <ChevronRight className="ml-auto size-4 text-fg-subtle transition-colors group-hover:text-accent" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
