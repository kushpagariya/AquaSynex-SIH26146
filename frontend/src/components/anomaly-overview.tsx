import type { AnomalyBucket } from "@/data/types"
import { cn } from "@/lib/utils"

export function AnomalyOverview({ series }: { series: AnomalyBucket[] }) {
  if (!series || series.length === 0) {
    return (
      <div className="flex h-52 w-full items-center justify-center text-xs text-fg-subtle">
        No transaction activity recorded in this dataset.
      </div>
    )
  }

  const maxTx = Math.max(...series.map((s) => s.transactions), 1)

  return (
    <div className="flex h-52 w-full min-w-0 items-stretch gap-1 sm:gap-2 px-1">
      {series.map((bucket, idx) => {
        const txPct = (bucket.transactions / maxTx) * 100
        const anomalyPct =
          bucket.transactions > 0 ? (bucket.anomalies / bucket.transactions) * 100 : 0
        const showLabel =
          series.length <= 8 ||
          idx % Math.ceil(series.length / 8) === 0 ||
          idx === series.length - 1

        return (
          <div
            key={`${bucket.label}-${idx}`}
            className="flex h-full min-w-0 flex-1 flex-col items-center gap-2"
          >
            <div className="flex min-h-0 w-full flex-1 items-end">
              <div
                className="relative w-full rounded-t bg-panel-2 transition-all hover:bg-panel-2/80"
                style={{ height: `${Math.max(txPct, 4)}%` }}
                title={`${bucket.transactions} transactions (${bucket.anomalies} anomalies) at ${bucket.label}`}
              >
                {bucket.anomalies > 0 ? (
                  <div
                    className="absolute inset-x-0 bottom-0 rounded-t bg-risk-high/70 transition-all hover:bg-risk-high"
                    style={{ height: `${anomalyPct}%` }}
                    title={`${bucket.anomalies} anomalies`}
                  />
                ) : null}
              </div>
            </div>
            <span
              className={cn(
                "w-full truncate text-center font-mono-id text-[10px] text-fg-subtle",
                !showLabel && "invisible",
              )}
            >
              {bucket.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
