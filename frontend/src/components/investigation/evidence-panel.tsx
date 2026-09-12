import { useState } from "react"
import {
  Activity,
  ArrowLeftRight,
  Network,
  Share2,
  BrainCircuit,
} from "lucide-react"
import type { EvidenceCategory, EvidenceItem } from "@/data/types"
import { SeverityBadge } from "@/components/ui/badges"
import { formatTime, cn } from "@/lib/utils"

const categoryMeta: Record<
  EvidenceCategory,
  { label: string; icon: typeof Activity }
> = {
  behavioral: { label: "Behavioral", icon: Activity },
  transaction: { label: "Transaction", icon: ArrowLeftRight },
  network: { label: "Network", icon: Network },
  connections: { label: "Connections", icon: Share2 },
  model: { label: "Model", icon: BrainCircuit },
}

const order: EvidenceCategory[] = [
  "behavioral",
  "transaction",
  "network",
  "connections",
  "model",
]

export function EvidencePanel({ items }: { items: EvidenceItem[] }) {
  const categories = order.filter((c) => items.some((i) => i.category === c))
  const [active, setActive] = useState<EvidenceCategory | "all">("all")

  const filtered =
    active === "all" ? items : items.filter((i) => i.category === active)

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 border-b border-line px-4 py-3">
        <FilterChip
          active={active === "all"}
          onClick={() => setActive("all")}
          label={`All (${items.length})`}
        />
        {categories.map((c) => {
          const Icon = categoryMeta[c].icon
          const count = items.filter((i) => i.category === c).length
          return (
            <FilterChip
              key={c}
              active={active === c}
              onClick={() => setActive(c)}
              label={`${categoryMeta[c].label} (${count})`}
              icon={<Icon className="size-3.5" />}
            />
          )
        })}
      </div>

      <ul className="divide-y divide-line-soft">
        {filtered.map((item) => {
          const Icon = categoryMeta[item.category].icon
          return (
            <li key={item.id} className="flex gap-3 px-4 py-3">
              <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded border border-line bg-panel-2 text-fg-subtle">
                <Icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-fg">{item.title}</p>
                  <SeverityBadge severity={item.severity} />
                </div>
                <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">
                  {item.detail}
                </p>
                {item.timestamp ? (
                  <span className="mt-1 inline-block font-mono-id text-[11px] text-fg-subtle">
                    {formatTime(item.timestamp)}
                  </span>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean
  onClick: () => void
  label: string
  icon?: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium transition-colors",
        active
          ? "border-accent/40 bg-accent-soft text-accent"
          : "border-line bg-panel-2 text-fg-muted hover:text-fg",
      )}
    >
      {icon}
      {label}
    </button>
  )
}
