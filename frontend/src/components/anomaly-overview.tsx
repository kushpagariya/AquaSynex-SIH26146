import type { AnomalyBucket } from "@/data/types"

export function AnomalyOverview({ series }: { series: AnomalyBucket[] }) {
  const maxTx = Math.max(...series.map((s) => s.transactions), 1)

  return (
    <div className="flex h-52 items-stretch gap-4 px-1">
      {series.map((bucket) => {
        const txPct = (bucket.transactions / maxTx) * 100
        const anomalyPct = (bucket.anomalies / bucket.transactions) * 100
        return (
          <div
            key={bucket.label}
            className="flex h-full flex-1 flex-col items-center gap-2"
          >
            <div className="flex min-h-0 w-full flex-1 items-end">
              <div
                className="relative w-full rounded-t bg-panel-2"
                style={{ height: `${txPct}%` }}
                title={`${bucket.transactions} transactions`}
              >
                <div
                  className="absolute inset-x-0 bottom-0 rounded-t bg-risk-high/70"
                  style={{ height: `${anomalyPct}%` }}
                  title={`${bucket.anomalies} anomalies`}
                />
              </div>
            </div>
            <span className="font-mono-id text-[10px] text-fg-subtle">
              {bucket.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
