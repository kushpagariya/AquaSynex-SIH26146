import { useEffect, useMemo, useRef, useState } from "react"
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"
import { Maximize2, Minus, Plus, Crosshair } from "lucide-react"
import type { GraphData, EntityType, Severity } from "@/data/types"
import { cn } from "@/lib/utils"

const typeColor: Record<EntityType, string> = {
  wallet: "#38bdf8",
  transaction: "#a78bfa",
  ip: "#f59e0b",
  network: "#f59e0b",
  exchange: "#22c55e",
  mixer: "#ef4444",
}

const severityColor: Record<Severity, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
}

export interface GraphSelection {
  id: string
  label: string
  type: EntityType
  severity?: Severity
  neighbors: number
}

export function GraphViewer({
  data,
  onSelect,
  className,
}: {
  data: GraphData
  onSelect?: (selection: GraphSelection | null) => void
  className?: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const elements = useMemo<ElementDefinition[]>(() => {
    const nodes = data.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.label,
        color: n.severity ? severityColor[n.severity] : typeColor[n.type],
        typeColor: typeColor[n.type],
        isFocus: n.isFocus ? 1 : 0,
        shape: n.type === "transaction" ? "round-rectangle" : "ellipse",
      },
    }))
    const edges = data.edges.map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.amount ? `${e.amount} BTC` : (e.label ?? ""),
        suspicious: e.suspicious ? 1 : 0,
      },
    }))
    return [...nodes, ...edges]
  }, [data])

  useEffect(() => {
    if (!containerRef.current) return

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#e6edf3",
            "font-size": "10px",
            "font-family": "JetBrains Mono, monospace",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-outline-color": "#0b0f14",
            "text-outline-width": 2,
            width: 34,
            height: 34,
            "border-width": 2,
            "border-color": "#0b0f14",
            shape: "data(shape)" as never,
          },
        },
        {
          selector: "node[isFocus = 1]",
          style: {
            width: 52,
            height: 52,
            "border-width": 3,
            "border-color": "#38bdf8",
            "font-size": "11px",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#26313d",
            "target-arrow-color": "#26313d",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.8,
            label: "data(label)",
            "font-size": "8px",
            "font-family": "JetBrains Mono, monospace",
            color: "#64748b",
            "text-rotation": "autorotate",
            "text-background-color": "#0b0f14",
            "text-background-opacity": 1,
            "text-background-padding": "2px",
          },
        },
        {
          selector: "edge[suspicious = 1]",
          style: {
            "line-color": "#f97316",
            "target-arrow-color": "#f97316",
            width: 2,
          },
        },
        {
          selector: ".faded",
          style: { opacity: 0.15 },
        },
        {
          selector: ".highlight",
          style: { "border-color": "#38bdf8", "border-width": 3 },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        padding: 30,
        nodeRepulsion: () => 12000,
        idealEdgeLength: () => 90,
      } as never,
      minZoom: 0.3,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
    })

    cyRef.current = cy

    cy.on("tap", "node", (evt) => {
      const node = evt.target
      const id = node.id()
      setSelectedId(id)

      cy.elements().addClass("faded")
      const hood = node.closedNeighborhood()
      hood.removeClass("faded")
      node.addClass("highlight")

      const raw = data.nodes.find((n) => n.id === id)
      if (raw && onSelect) {
        onSelect({
          id: raw.id,
          label: raw.label,
          type: raw.type,
          severity: raw.severity,
          neighbors: node.neighborhood("node").length,
        })
      }
    })

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedId(null)
        cy.elements().removeClass("faded highlight")
        onSelect?.(null)
      }
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [elements, data.nodes, onSelect])

  function zoomBy(factor: number) {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  function fit() {
    cyRef.current?.fit(undefined, 40)
  }

  return (
    <div className={cn("relative h-full w-full", className)}>
      <div ref={containerRef} className="panel-grid h-full w-full" />

      <div className="absolute right-3 top-3 flex flex-col gap-1.5">
        <GraphButton label="Zoom in" onClick={() => zoomBy(1.25)}>
          <Plus className="size-4" />
        </GraphButton>
        <GraphButton label="Zoom out" onClick={() => zoomBy(0.8)}>
          <Minus className="size-4" />
        </GraphButton>
        <GraphButton label="Fit to view" onClick={fit}>
          <Maximize2 className="size-4" />
        </GraphButton>
      </div>

      {selectedId ? (
        <button
          type="button"
          onClick={() => {
            cyRef.current?.elements().removeClass("faded highlight")
            setSelectedId(null)
            onSelect?.(null)
          }}
          className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded border border-line bg-panel/90 px-2.5 py-1.5 text-xs text-fg-muted backdrop-blur hover:text-accent"
        >
          <Crosshair className="size-3.5" />
          Clear selection
        </button>
      ) : null}
    </div>
  )
}

function GraphButton({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="grid size-8 place-items-center rounded border border-line bg-panel/90 text-fg-muted backdrop-blur transition-colors hover:border-accent/50 hover:text-accent"
    >
      {children}
    </button>
  )
}
