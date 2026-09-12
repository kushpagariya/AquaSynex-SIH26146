import type { RiskProfile } from "@/data/types"
import { severityColorVar } from "@/components/ui/badges"

export function RiskFactors({ risk }: { risk: RiskProfile }) {
  return (
    <div className="space-y-4">
      {risk.summary ? (
        <p className="text-sm leading-relaxed text-fg-muted">{risk.summary}</p>
      ) : null}
      <ul className="space-y-3">
        {risk.factors.map((factor) => {
          const color = severityColorVar(risk.severity)
          return (
            <li key={factor.id}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-sm font-medium text-fg">
                    {factor.label}
                  </span>
                </div>
                <span className="font-mono-id text-xs tabular-nums text-fg-subtle">
                  {Math.round(factor.weight * 100)}%
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-panel-2">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${factor.weight * 100}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
              <p className="mt-1 pl-4 text-xs text-fg-subtle">
                {factor.description}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
