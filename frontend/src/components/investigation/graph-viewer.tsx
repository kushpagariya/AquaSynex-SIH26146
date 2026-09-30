import { useEffect, useMemo, useRef, useState } from "react"
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"
import { Maximize2, Minus, Plus, Crosshair } from "lucide-react"
import type { GraphData, EntityType, Severity } from "@/data/types"
import { cn } from "@/lib/utils"

const typeColor: Record<EntityType, string> = {
  wallet: "#475569", // slate charcoal
  transaction: "#173B63", // deep navy
  ip: "#A46A16", // muted amber
  network: "#A46A16", // muted amber
  exchange: "#2F6B4F", // muted green
  mixer: "#A63D3D", // muted red
  cluster: "#6366F1", // indigo
}

const severityColor: Record<Severity, string> = {
  low: "#2F6B4F",
  medium: "#A46A16",
  high: "#B85D1B",
  critical: "#A63D3D",
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
        color: n.severity ? severityColor[n.severity] : typeColor[n.type] || "#475569",
        typeColor: typeColor[n.type] || "#475569",
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
            color: "#171717",
            "font-size": "10px",
            "font-family": "Inter, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-outline-color": "#FFFFFF",
            "text-outline-width": 2,
            width: 32,
            height: 32,
            "border-width": 1.5,
            "border-color": "#FFFFFF",
            shape: "data(shape)" as never,
          },
        },
        {
          selector: "node[isFocus = 1]",
          style: {
            width: 46,
            height: 46,
            "border-width": 2.5,
            "border-color": "#173B63",
            "font-size": "11px",
            "font-weight": "bold",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#CBD5E1",
            "target-arrow-color": "#CBD5E1",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.8,
            label: "data(label)",
            "font-size": "9px",
            "font-family": "JetBrains Mono, monospace",
            color: "#64748B",
            "text-rotation": "autorotate",
            "text-background-color": "#FFFFFF",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
          },
        },
        {
          selector: "edge[suspicious = 1]",
          style: {
            "line-color": "#B85D1B",
            "target-arrow-color": "#B85D1B",
            width: 2,
          },
        },
        {
          selector: ".faded",
          style: { opacity: 0.2 },
        },
        {
          selector: ".highlight",
          style: {
            "border-color": "#173B63",
            "border-width": 3,
            "line-color": "#173B63",
            "target-arrow-color": "#173B63",
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        padding: 30,
        nodeRepulsion: () => 10000,
        idealEdgeLength: () => 80,
      } as never,
      minZoom: 0.25,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
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
          neighbors: hood.nodes().length - 1,
        })
      }
    })

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedId(null)
        cy.elements().removeClass("faded").removeClass("highlight")
        if (onSelect) onSelect(null)
      }
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [elements, data, onSelect])

  return (
    <div
      className={cn(
        "relative h-96 w-full overflow-hidden rounded-lg border border-line bg-[#F8F9FA]",
        className,
      )}
    >
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute bottom-3 right-3 flex items-center gap-1 rounded border border-line bg-panel p-1 shadow-sm">
        <button
          type="button"
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
          className="rounded p-1 text-fg-muted hover:bg-panel-2 hover:text-fg"
          aria-label="Zoom in"
        >
          <Plus className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
          className="rounded p-1 text-fg-muted hover:bg-panel-2 hover:text-fg"
          aria-label="Zoom out"
        >
          <Minus className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => cyRef.current?.fit(undefined, 30)}
          className="rounded p-1 text-fg-muted hover:bg-panel-2 hover:text-fg"
          aria-label="Reset view"
        >
          <Crosshair className="size-3.5" />
        </button>
      </div>
    </div>
  )
}
