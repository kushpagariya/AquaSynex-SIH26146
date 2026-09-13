import { useEffect, useRef, useState, useMemo } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"
import {
  Share2,
  Search,
  Maximize2,
  Minimize2,
  Plus,
  Minus,
  Crosshair,
  Layers,
  Filter,
  ExternalLink,
  ShieldAlert,
  ArrowRight,
  Clock,
  X,
  RefreshCw,
  GitFork,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getAnalysisGraph, getAddressSubgraph } from "@/api"
import { getActiveContext } from "@/data/service"
import type { GraphExport, GraphNodeDto, GraphEdgeDto } from "@/api/types"
import type { EntityType, Severity } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber, cn } from "@/lib/utils"

const typeColors: Record<string, string> = {
  wallet: "#38bdf8",
  address: "#38bdf8",
  transaction: "#a78bfa",
  ip: "#f59e0b",
  network: "#f59e0b",
  exchange: "#22c55e",
  mixer: "#ef4444",
}

const severityColors: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
}

interface SelectedNodeInfo {
  id: string
  label: string
  type: string
  riskScore?: number
  riskLevel?: string
  metadata?: {
    transactionCount?: number
    totalReceivedBtc?: string
    totalSentBtc?: string
    firstSeen?: string
    lastSeen?: string
    activeDays?: number
  }
}

interface SelectedEdgeInfo {
  id: string
  source: string
  target: string
  totalValueBtc: string
  transactionCount: number
  transactions: {
    transactionId: string
    valueBtc: string
    timestamp?: string
  }[]
}

export function GraphExplorerPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusParam = searchParams.get("focus") || ""

  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [rawGraph, setRawGraph] = useState<GraphExport | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Search & Navigation
  const [searchQuery, setSearchQuery] = useState(focusParam)
  const [currentHops, setCurrentHops] = useState(2)

  // Inspection states
  const [selectedNode, setSelectedNode] = useState<SelectedNodeInfo | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdgeInfo | null>(null)

  // Filters
  const [nodeTypeFilter, setNodeTypeFilter] = useState<Record<string, boolean>>({
    address: true,
    transaction: true,
  })
  const [suspiciousOnly, setSuspiciousOnly] = useState(false)
  const [minEdgeBtc, setMinEdgeBtc] = useState(0)

  // Load canonical full graph or focused subgraph
  async function loadGraphData(targetAddressId?: string, hops = 2) {
    setLoading(true)
    setErrorMsg(null)
    setSelectedNode(null)
    setSelectedEdge(null)

    try {
      const { analysisId } = await getActiveContext()
      if (!analysisId) {
        setLoading(false)
        return
      }

      let exportData: GraphExport
      if (targetAddressId) {
        exportData = await getAddressSubgraph(targetAddressId, { hops, analysisId })
      } else {
        exportData = await getAnalysisGraph(analysisId, { maxNodes: 500, includeNeighbors: true })
      }
      setRawGraph(exportData)
      setLoading(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load graph export from backend")
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGraphData(focusParam || undefined, currentHops)
  }, [focusParam])

  // Build Cytoscape elements from rawGraph with filters applied
  const elements = useMemo<ElementDefinition[]>(() => {
    if (!rawGraph) return []

    const validNodeIds = new Set<string>()
    const nodes: ElementDefinition[] = []

    for (const n of rawGraph.nodes) {
      const nType = (n.nodeType || "address").toLowerCase()
      if (nodeTypeFilter[nType] === false) continue
      if (suspiciousOnly && (!n.riskLevel || (n.riskLevel !== "high" && n.riskLevel !== "critical"))) {
        continue
      }

      validNodeIds.add(n.id)
      const color = n.riskLevel ? severityColors[n.riskLevel.toLowerCase()] || typeColors[nType] : typeColors[nType] || "#38bdf8"
      const isFocused = Boolean(focusParam && n.id === focusParam)

      nodes.push({
        data: {
          id: n.id,
          label: n.label || `${n.id.slice(0, 8)}…`,
          nodeType: nType,
          riskScore: n.riskScore,
          riskLevel: n.riskLevel,
          color,
          shape: nType === "transaction" ? "round-rectangle" : "ellipse",
          isFocus: isFocused ? 1 : 0,
        },
      })
    }

    const edges: ElementDefinition[] = []
    for (const e of rawGraph.edges) {
      if (!validNodeIds.has(e.source) || !validNodeIds.has(e.target)) continue
      const valBtc = parseFloat(e.totalValueBtc || "0")
      if (valBtc < minEdgeBtc) continue

      const isSuspicious = (e.totalValueSatoshi || 0) > 100_000_000 || valBtc >= 1.0

      edges.push({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: valBtc > 0 ? `${valBtc.toFixed(4)} BTC` : "",
          totalValueBtc: e.totalValueBtc,
          transactionCount: e.transactionCount,
          transactions: e.transactions,
          suspicious: isSuspicious ? 1 : 0,
        },
      })
    }

    return [...nodes, ...edges]
  }, [rawGraph, nodeTypeFilter, suspiciousOnly, minEdgeBtc, focusParam])

  // Initialize Cytoscape
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
            width: 36,
            height: 36,
            "border-width": 2,
            "border-color": "#0b0f14",
            shape: "data(shape)" as never,
          },
        },
        {
          selector: "node[isFocus = 1]",
          style: {
            width: 54,
            height: 54,
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
            "arrow-scale": 0.85,
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
            width: 2.5,
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
        {
          selector: "edge.highlight",
          style: { "line-color": "#38bdf8", "target-arrow-color": "#38bdf8", width: 2.5 },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        padding: 40,
        nodeRepulsion: () => 14000,
        idealEdgeLength: () => 100,
      } as never,
      minZoom: 0.2,
      maxZoom: 3.0,
      wheelSensitivity: 0.2,
    })

    cyRef.current = cy

    // Handle node tap
    cy.on("tap", "node", (evt) => {
      const node = evt.target
      const id = node.id()

      cy.elements().addClass("faded")
      const hood = node.closedNeighborhood()
      hood.removeClass("faded")
      node.addClass("highlight")

      const raw = rawGraph?.nodes.find((n) => n.id === id)
      if (raw) {
        setSelectedNode({
          id: raw.id,
          label: raw.label,
          type: raw.nodeType,
          riskScore: raw.riskScore ? Math.round(raw.riskScore * 100) : undefined,
          riskLevel: raw.riskLevel,
          metadata: raw.metadata,
        })
        setSelectedEdge(null)
      }
    })

    // Handle edge tap
    cy.on("tap", "edge", (evt) => {
      const edge = evt.target
      const id = edge.id()

      cy.elements().addClass("faded")
      edge.removeClass("faded").addClass("highlight")
      edge.source().removeClass("faded").addClass("highlight")
      edge.target().removeClass("faded").addClass("highlight")

      const raw = rawGraph?.edges.find((e) => e.id === id)
      if (raw) {
        setSelectedEdge({
          id: raw.id,
          source: raw.source,
          target: raw.target,
          totalValueBtc: raw.totalValueBtc,
          transactionCount: raw.transactionCount,
          transactions: raw.transactions || [],
        })
        setSelectedNode(null)
      }
    })

    // Clear on background tap
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("faded highlight")
        setSelectedNode(null)
        setSelectedEdge(null)
      }
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [elements, rawGraph])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!searchQuery.trim()) {
      loadGraphData(undefined, currentHops)
      return
    }
    loadGraphData(searchQuery.trim(), currentHops)
  }

  function handleHopChange(hops: number) {
    setCurrentHops(hops)
    loadGraphData(searchQuery.trim() || undefined, hops)
  }

  function zoomBy(factor: number) {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  function fit() {
    cyRef.current?.fit(undefined, 40)
  }

  return (
    <AppLayout title="Graph Explorer">
      <div className={cn("space-y-4", isFullscreen && "fixed inset-0 z-50 bg-bg p-6 overflow-hidden")}>
        {/* Top Search & Filter Bar */}
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-3 p-3.5">
            {/* Search */}
            <form onSubmit={handleSearchSubmit} className="flex min-w-[300px] flex-1 items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 size-4 text-fg-subtle" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Focus address or TXID (subgraph center)..."
                  className="w-full rounded-md border border-line bg-panel-2 py-1.5 pl-9 pr-3 text-xs font-mono-id text-fg focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="submit"
                className="rounded border border-accent/40 bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent/10"
              >
                Focus
              </button>
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("")
                    loadGraphData(undefined, currentHops)
                  }}
                  className="rounded border border-line bg-panel-2 px-2.5 py-1.5 text-xs text-fg-muted hover:text-fg"
                >
                  Reset
                </button>
              ) : null}
            </form>

            {/* Hops Expansion Selector */}
            <div className="flex items-center gap-1.5 rounded-md border border-line bg-panel-2 p-1 text-xs">
              <span className="px-2 font-medium text-fg-subtle flex items-center gap-1">
                <GitFork className="size-3.5" />
                Hops:
              </span>
              {[1, 2, 3].map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => handleHopChange(h)}
                  className={cn(
                    "rounded px-2.5 py-1 text-xs font-semibold transition-colors",
                    currentHops === h ? "bg-accent-soft text-accent" : "text-fg-muted hover:text-fg",
                  )}
                >
                  {h}-hop
                </button>
              ))}
            </div>

            {/* Quick Filters */}
            <div className="flex items-center gap-2 text-xs">
              <label className="flex items-center gap-1.5 cursor-pointer text-fg-muted hover:text-fg">
                <input
                  type="checkbox"
                  checked={suspiciousOnly}
                  onChange={(e) => setSuspiciousOnly(e.target.checked)}
                  className="rounded border-line bg-panel-2 accent-accent"
                />
                High Risk Only
              </label>
              <button
                type="button"
                onClick={() => loadGraphData(searchQuery.trim() || undefined, currentHops)}
                className="flex items-center gap-1 rounded border border-line bg-panel-2 px-2.5 py-1 text-fg-muted hover:text-accent"
              >
                <RefreshCw className="size-3" />
                Reload
              </button>
              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="flex items-center gap-1 rounded border border-line bg-panel-2 px-2.5 py-1 text-fg-muted hover:text-accent"
              >
                {isFullscreen ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
                {isFullscreen ? "Exit" : "Full"}
              </button>
            </div>
          </div>
        </Panel>

        {/* Canvas & Right-side Inspector */}
        <div className="relative flex h-[720px] overflow-hidden rounded-[var(--radius-panel)] border border-line bg-panel">
          {/* Main Cytoscape Canvas */}
          <div className="relative flex-1 h-full">
            {loading ? (
              <LoadingState label="Computing topological graph layout" />
            ) : errorMsg ? (
              <ErrorState title="Graph Rendering Error" description={errorMsg} />
            ) : !rawGraph || !rawGraph.nodes.length ? (
              <EmptyState title="No graph nodes found" description="Select a dataset with address relations." />
            ) : (
              <div ref={containerRef} className="panel-grid h-full w-full" />
            )}

            {/* Canvas Controls */}
            <div className="absolute left-3 bottom-3 flex items-center gap-2 rounded border border-line bg-panel/90 px-3 py-1.5 text-xs text-fg-subtle backdrop-blur">
              <span className="font-mono-id">
                {rawGraph?.nodeCount ?? 0} nodes • {rawGraph?.edgeCount ?? 0} edges
              </span>
              {rawGraph?.isSubgraph ? (
                <span className="rounded bg-accent-soft px-1.5 py-0.5 text-[10px] text-accent">
                  Subgraph ({currentHops}-hop)
                </span>
              ) : null}
            </div>

            <div className="absolute right-3 top-3 flex flex-col gap-1.5">
              <button
                type="button"
                onClick={() => zoomBy(1.25)}
                className="grid size-8 place-items-center rounded border border-line bg-panel/90 text-fg-muted backdrop-blur hover:text-accent"
                aria-label="Zoom in"
              >
                <Plus className="size-4" />
              </button>
              <button
                type="button"
                onClick={() => zoomBy(0.8)}
                className="grid size-8 place-items-center rounded border border-line bg-panel/90 text-fg-muted backdrop-blur hover:text-accent"
                aria-label="Zoom out"
              >
                <Minus className="size-4" />
              </button>
              <button
                type="button"
                onClick={fit}
                className="grid size-8 place-items-center rounded border border-line bg-panel/90 text-fg-muted backdrop-blur hover:text-accent"
                aria-label="Fit view"
              >
                <Crosshair className="size-4" />
              </button>
            </div>
          </div>

          {/* Right-Side Inspector Panel */}
          {(selectedNode || selectedEdge) && (
            <div className="w-80 shrink-0 border-l border-line bg-panel/95 p-4 backdrop-blur overflow-y-auto space-y-4 shadow-xl shadow-black/40">
              <div className="flex items-start justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-fg-subtle">
                  {selectedNode ? "Node Inspector" : "Edge Inspector"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedNode(null)
                    setSelectedEdge(null)
                    cyRef.current?.elements().removeClass("faded highlight")
                  }}
                  className="text-fg-subtle hover:text-fg"
                >
                  <X className="size-4" />
                </button>
              </div>

              {/* Node Inspector Content */}
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="font-mono-id text-sm font-semibold text-fg break-all">
                      {selectedNode.label}
                    </h3>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <span className="rounded border border-line bg-panel-2 px-2 py-0.5 text-[11px] font-medium capitalize text-fg-muted">
                        {selectedNode.type}
                      </span>
                      {selectedNode.riskLevel ? (
                        <SeverityBadge severity={selectedNode.riskLevel.toLowerCase() as Severity} />
                      ) : null}
                    </div>
                  </div>

                  {selectedNode.riskScore !== undefined ? (
                    <div className="rounded border border-line bg-panel-2 p-3">
                      <span className="text-[11px] text-fg-subtle">Aggregate ML Risk</span>
                      <p
                        className="font-mono-id text-xl font-bold tabular-nums"
                        style={{ color: severityColorVar((selectedNode.riskLevel?.toLowerCase() as Severity) || "low") }}
                      >
                        {selectedNode.riskScore} / 100
                      </p>
                      <p className="mt-1 text-[10px] text-fg-subtle">
                        Aggregated from associated transaction predictions.
                      </p>
                    </div>
                  ) : null}

                  {selectedNode.metadata ? (
                    <div className="space-y-2 text-xs divide-y divide-line-soft">
                      <div className="flex justify-between py-1.5">
                        <span className="text-fg-subtle">Transactions:</span>
                        <span className="font-mono-id text-fg">{selectedNode.metadata.transactionCount ?? "—"}</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-fg-subtle">Total Received:</span>
                        <span className="font-mono-id text-fg">{selectedNode.metadata.totalReceivedBtc ?? "—"} BTC</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-fg-subtle">Total Sent:</span>
                        <span className="font-mono-id text-fg">{selectedNode.metadata.totalSentBtc ?? "—"} BTC</span>
                      </div>
                      <div className="flex justify-between py-1.5">
                        <span className="text-fg-subtle">Active Days:</span>
                        <span className="font-mono-id text-fg">{selectedNode.metadata.activeDays ?? "—"} days</span>
                      </div>
                    </div>
                  ) : null}

                  <div className="space-y-2 pt-2 border-t border-line">
                    <button
                      type="button"
                      onClick={() => navigate(`/investigation/${selectedNode.id}?entityType=${selectedNode.type}`)}
                      className="w-full rounded border border-accent/40 bg-accent-soft py-2 text-xs font-medium text-accent hover:bg-accent/10"
                    >
                      Investigate Node in Detail →
                    </button>
                    <button
                      type="button"
                      onClick={() => handleHopChange(currentHops >= 3 ? 1 : currentHops + 1)}
                      className="w-full rounded border border-line bg-panel-2 py-1.5 text-xs text-fg hover:text-accent"
                    >
                      Expand Neighborhood (+1 Hop)
                    </button>
                  </div>
                </div>
              ) : selectedEdge ? (
                /* Edge Inspector Content */
                <div className="space-y-4">
                  <div>
                    <span className="text-[11px] text-fg-subtle uppercase">Transaction Flow</span>
                    <p className="mt-1 font-mono-id text-lg font-bold text-fg">
                      {selectedEdge.totalValueBtc} BTC
                    </p>
                    <p className="text-xs text-fg-subtle">
                      {selectedEdge.transactionCount} transaction{selectedEdge.transactionCount === 1 ? "" : "s"} aggregated
                    </p>
                  </div>

                  <div className="space-y-2 text-xs rounded border border-line bg-panel-2 p-3">
                    <div>
                      <span className="text-[10px] text-fg-subtle uppercase">Source Address</span>
                      <MonoId value={selectedEdge.source} head={10} tail={8} className="mt-0.5 block" />
                    </div>
                    <div className="pt-2 border-t border-line-soft">
                      <span className="text-[10px] text-fg-subtle uppercase">Target Address</span>
                      <MonoId value={selectedEdge.target} head={10} tail={8} className="mt-0.5 block" />
                    </div>
                  </div>

                  {selectedEdge.transactions.length ? (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-fg-subtle uppercase tracking-wider">
                        Contained Transactions ({selectedEdge.transactions.length})
                      </span>
                      <div className="max-h-44 space-y-1.5 overflow-y-auto">
                        {selectedEdge.transactions.map((t) => (
                          <div
                            key={t.transactionId}
                            onClick={() => navigate(`/investigation/${t.transactionId}?entityType=transaction`)}
                            className="cursor-pointer rounded border border-line-soft bg-panel-2 p-2 hover:border-accent/40"
                          >
                            <MonoId value={t.transactionId} head={8} tail={6} copyable={false} />
                            <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
                              <span>{t.valueBtc} BTC</span>
                              <span className="font-mono-id text-fg-subtle">
                                {t.timestamp ? formatDateTime(t.timestamp) : "—"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
