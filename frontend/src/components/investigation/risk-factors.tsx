import type { RiskProfile } from "@/data/types"

export function RiskFactors({ risk }: { risk: RiskProfile }) {
  // Disclose top 5 model contributors for high-conviction decision making
  const topFactors = risk.factors.slice(0, 5)

  return (
    <div className="space-y-4 font-sans">
      {risk.summary ? (
        <p className="text-xs leading-relaxed text-fg-muted border-l-2 border-accent pl-3 py-0.5">
          {risk.summary}
        </p>
      ) : null}
      <ul className="space-y-3 pt-1">
        {topFactors.map((factor) => {
          // SHAP feature contribution:
          // Weight > 0 contributes to risk (suspicious: muted red #A63D3D)
          // Weight < 0 decreases risk (mitigating / normal: muted slate/blue #60758C)
          const isMitigating = factor.weight < 0
          const barColor = isMitigating ? "#60758C" : "#A63D3D"
          const pct = Math.min(Math.round(Math.abs(factor.weight) * 100), 100)

          return (
            <li key={factor.id} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-fg font-sans">{factor.label}</span>
                <span className="font-mono text-[11px] tabular-nums font-semibold" style={{ color: barColor }}>
                  {isMitigating ? `-${pct}% (Mitigating)` : `+${pct}% (Risk Factor)`}
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded bg-panel-2 border border-line-soft">
                <div
                  className="h-full rounded transition-all duration-300"
                  style={{
                    width: `${Math.max(pct, 4)}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
              <p className="text-[11px] text-fg-subtle leading-normal">
                {factor.description}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
