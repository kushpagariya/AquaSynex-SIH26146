import { useEffect, useRef, useState, useMemo, useCallback } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"
import {
  Search,
  Maximize2,
  Minimize2,
  Plus,
  Minus,
  Crosshair,
  X,
  RefreshCw,
  GitFork,
  Copy,
  Check,
  ShieldAlert,
  AlertTriangle,
  Network,
  Clock,
  Cpu,
  ExternalLink,
  Activity,
  Info,
  Layers,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import {
  getAnalysisGraph,
  getGraphNeighborhood,
  listTransactions,
  listAddresses,
} from "@/api"
import { getActiveContext } from "@/data/service"
import type { GraphExport, GraphNodeDto, GraphEdgeDto } from "@/api/types"
import type { Severity } from "@/data/types"
import { formatDateTime, cn } from "@/lib/utils"

// Institutional forensic palette
const typeColors: Record<string, string> = {
  wallet: "#3B6D9C",
  address: "#3B6D9C",
  transaction: "#173B63",
  cluster: "#4F46E5",
  ip: "#A46A16",
  network: "#A46A16",
  exchange: "#2F6B4F",
  mixer: "#A63D3D",
}

const severityColors: Record<string, string> = {
  low: "#2F6B4F",
  medium: "#A46A16",
  high: "#B85D1B",
  critical: "#A63D3D",
}

interface SelectedNodeInfo {
  id: string
  label: string
  type: string
  riskScore?: number
  riskLevel?: string
  behaviorType?: string
  alerts?: Record<string, any>[]
  metadata?: Record<string, any>
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
  const [searchParams, setSearchParams] = useSearchParams()
  const focusParam = searchParams.get("focus") || ""

  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  // Mode: "investigation" (focused neighborhood) vs "full" (full connections)
  const [viewMode, setViewMode] = useState<"investigation" | "full">("investigation")

  // Graph data & query state
  const [rawGraph, setRawGraph] = useState<GraphExport | null>(null)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Search & Navigation
  const [searchQuery, setSearchQuery] = useState(focusParam)
  const [currentHops, setCurrentHops] = useState(2)

  // Inspection states
  const [selectedNode, setSelectedNode] = useState<SelectedNodeInfo | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdgeInfo | null>(null)
  const [copiedId, setCopiedId] = useState(false)

  // Filters
  const [suspiciousOnly, setSuspiciousOnly] = useState(false)

  // Quick investigation suggestions for initial empty state
  const [sampleTxid, setSampleTxid] = useState<string | null>(null)
  const [sampleAddress, setSampleAddress] = useState<string | null>(null)

  // Fetch sample suggestion entities once on mount
  useEffect(() => {
    async function loadSamples() {
      try {
        const { datasetId } = await getActiveContext()
        if (datasetId) {
          const [txsRes, addrsRes] = await Promise.all([
            listTransactions(datasetId, { page: 1, pageSize: 3 }).catch(() => null),
            listAddresses(datasetId, { page: 1, pageSize: 3 }).catch(() => null),
          ])
          if (txsRes?.data?.[0]?.transactionId) {
            setSampleTxid(txsRes.data[0].transactionId)
          }
          if (addrsRes?.data?.[0]?.addressId) {
            setSampleAddress(addrsRes.data[0].addressId)
          }
        }
      } catch {
        // Sample loading is non-critical
      }
    }
    loadSamples()
  }, [])

  // Load graph data based on mode, target entity, hops, and risk filter
  const loadGraphData = useCallback(
    async (
      targetEntityId?: string,
      hops = 2,
      mode: "investigation" | "full" = viewMode,
      highRisk = suspiciousOnly,
    ) => {
      // In investigation mode, if no entity is queried or focused, return to empty state
      if (mode === "investigation" && !targetEntityId) {
        setRawGraph(null)
        setSelectedNode(null)
        setSelectedEdge(null)
        setLoading(false)
        setErrorMsg(null)
        return
      }

      setLoading(true)
      setErrorMsg(null)

      try {
        const { analysisId, datasetId } = await getActiveContext()
        if (!analysisId && !datasetId) {
          setErrorMsg("No active dataset or analysis found.")
          setLoading(false)
          return
        }

        let exportData: GraphExport

        if (mode === "full") {
          // Mode 2: Full Connection Mode (constrained to active analysis)
          exportData = await getAnalysisGraph(analysisId || datasetId!, {
            maxNodes: 500,
            includeNeighbors: true,
            minRiskScore: highRisk ? 0.50 : undefined,
          })
        } else {
          // Mode 1: Investigation Mode (focused bipartite multi-hop neighborhood)
          exportData = await getGraphNeighborhood(targetEntityId!, {
            depth: hops,
            analysisId: analysisId || undefined,
            datasetId: datasetId || undefined,
            highRiskOnly: highRisk,
          })
        }

        setRawGraph(exportData)

        // Select and inspect the target entity if specified
        if (targetEntityId && exportData.nodes.length > 0) {
          const matched = exportData.nodes.find(
            (n) => n.id.toLowerCase() === targetEntityId.toLowerCase(),
          )
          const nodeToSelect = matched || exportData.nodes[0]
          const rawScore = nodeToSelect.riskScore
          setSelectedNode({
            id: nodeToSelect.id,
            label: nodeToSelect.label,
            type: nodeToSelect.nodeType || "address",
            riskScore:
              rawScore !== undefined && rawScore !== null
                ? Math.round(rawScore > 1 ? rawScore : rawScore * 100)
                : undefined,
            riskLevel: nodeToSelect.riskLevel,
            behaviorType: nodeToSelect.behaviorType,
            alerts: nodeToSelect.alerts || nodeToSelect.metadata?.alerts,
            metadata: nodeToSelect.metadata,
          })
          setSelectedEdge(null)
        }

        setLoading(false)
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load graph"
        setErrorMsg(msg)
        setLoading(false)
      }
    },
    [viewMode, suspiciousOnly],
  )

  // Trigger loading when focusParam changes
  useEffect(() => {
    if (focusParam) {
      setSearchQuery(focusParam)
      loadGraphData(focusParam, currentHops, viewMode, suspiciousOnly)
    }
  }, [focusParam])

  // Handle Search Submission
  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = searchQuery.trim()
    if (!trimmed) {
      setSearchParams({})
      loadGraphData(undefined, currentHops, viewMode, suspiciousOnly)
      return
    }
    setSearchParams({ focus: trimmed })
    loadGraphData(trimmed, currentHops, viewMode, suspiciousOnly)
  }

  // Handle Hop Depth Change
  function handleHopChange(hops: number) {
    setCurrentHops(hops)
    if (viewMode === "investigation") {
      const target = searchQuery.trim() || focusParam || selectedNode?.id
      if (target) {
        loadGraphData(target, hops, "investigation", suspiciousOnly)
      }
    }
  }

  // Handle Mode Change between Investigation and Full Connections
  function handleModeChange(newMode: "investigation" | "full") {
    setViewMode(newMode)
    const target = searchQuery.trim() || focusParam || selectedNode?.id
    loadGraphData(target || undefined, currentHops, newMode, suspiciousOnly)
  }

  // Handle High-Risk Filter Toggle
  function handleHighRiskToggle(checked: boolean) {
    setSuspiciousOnly(checked)
    const target = searchQuery.trim() || focusParam || selectedNode?.id
    loadGraphData(target || undefined, currentHops, viewMode, checked)
  }

  // Copy identifier to clipboard with confirmation
  function handleCopyIdentifier(id: string) {
    navigator.clipboard.writeText(id)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  // Summary statistics calculated strictly from currently loaded graph data
  const summaryStats = useMemo(() => {
    if (!rawGraph) {
      return {
        txCount: 0,
        addrCount: 0,
        clusterCount: 0,
        highRiskCount: 0,
        criticalRiskCount: 0,
        totalNodes: 0,
        totalEdges: 0,
      }
    }

    let txs = 0
    let addrs = 0
    let clusters = 0
    let high = 0
    let critical = 0

    for (const n of rawGraph.nodes) {
      const t = (n.nodeType || "address").toLowerCase()
      if (t === "transaction") txs++
      else if (t === "cluster") clusters++
      else addrs++

      const lvl = (n.riskLevel || "").toLowerCase()
      const score = n.riskScore || 0
      if (lvl === "critical" || score >= 0.80) {
        critical++
      } else if (lvl === "high" || score >= 0.50) {
        high++
      }
    }

    return {
      txCount: txs,
      addrCount: addrs,
      clusterCount: clusters,
      highRiskCount: high,
      criticalRiskCount: critical,
      totalNodes: rawGraph.nodes.length,
      totalEdges: rawGraph.edges.length,
    }
  }, [rawGraph])

  // Build Cytoscape elements with restrained forensic typography and selective labeling
  const elements = useMemo<ElementDefinition[]>(() => {
    if (!rawGraph) return []

    const validNodeIds = new Set<string>()
    const nodes: ElementDefinition[] = []
    const focusedId = searchQuery.trim() || focusParam || selectedNode?.id || ""

    for (const n of rawGraph.nodes) {
      const nType = (n.nodeType || "address").toLowerCase()
      const lvl = (n.riskLevel || "").toLowerCase()
      const score = n.riskScore ?? 0

      // Enforce high-risk filter if active (risk_score >= 0.50 or high/critical)
      if (suspiciousOnly && score < 0.50 && lvl !== "high" && lvl !== "critical" && n.id !== focusedId) {
        continue
      }

      validNodeIds.add(n.id)
      const isFocused = Boolean(focusedId && n.id.toLowerCase() === focusedId.toLowerCase())
      const isSelected = Boolean(selectedNode && n.id.toLowerCase() === selectedNode.id.toLowerCase())
      const isHighRisk = lvl === "high" || lvl === "critical" || score >= 0.50

      // Color mapping with restrained semantic emphasis
      let nodeColor = typeColors[nType] || "#3B6D9C"
      if (lvl === "critical" || score >= 0.80) {
        nodeColor = severityColors.critical
      } else if (lvl === "high" || score >= 0.50) {
        nodeColor = severityColors.high
      } else if (lvl === "medium" || score >= 0.25) {
        nodeColor = severityColors.medium
      }

      // Show labels primarily for selected node, focused node, or high-risk entities
      const displayLabel =
        isFocused || isSelected || isHighRisk || rawGraph.nodes.length <= 15
          ? n.label || `${n.id.slice(0, 8)}…`
          : ""

      nodes.push({
        data: {
          id: n.id,
          label: displayLabel,
          nodeType: nType,
          riskScore: n.riskScore,
          riskLevel: n.riskLevel,
          color: nodeColor,
          shape: nType === "transaction" ? "round-rectangle" : nType === "cluster" ? "hexagon" : "ellipse",
          isFocus: isFocused ? 1 : 0,
          isSelected: isSelected ? 1 : 0,
        },
      })
    }

    const edges: ElementDefinition[] = []
    for (const e of rawGraph.edges) {
      if (!validNodeIds.has(e.source) || !validNodeIds.has(e.target)) continue
      const valBtc = parseFloat(e.totalValueBtc || "0")
      const isSuspicious = (e.totalValueSatoshi || 0) > 100_000_000 || valBtc >= 1.0

      edges.push({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: valBtc > 0 ? `${valBtc.toFixed(3)} BTC` : "",
          totalValueBtc: e.totalValueBtc,
          transactionCount: e.transactionCount,
          transactions: e.transactions || [],
          suspicious: isSuspicious ? 1 : 0,
        },
      })
    }

    return [...nodes, ...edges]
  }, [rawGraph, suspiciousOnly, searchQuery, focusParam, selectedNode])

  // Initialize and update Cytoscape canvas
  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#1E293B",
            "font-size": "10px",
            "font-family": "Inter, monospace, sans-serif",
            "font-weight": "bold",
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
            width: 44,
            height: 44,
            "border-width": 3.5,
            "border-color": "#0F172A",
            "font-size": "11px",
            "font-weight": "bold",
          },
        },
        {
          selector: "node[isSelected = 1]",
          style: {
            "border-width": 3,
            "border-color": "#173B63",
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
            "font-family": "monospace",
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
            width: 2.2,
          },
        },
        {
          selector: ".faded",
          style: { opacity: 0.15 },
        },
        {
          selector: ".highlight",
          style: { "border-color": "#0F172A", "border-width": 3 },
        },
        {
          selector: "edge.highlight",
          style: { "line-color": "#173B63", "target-arrow-color": "#173B63", width: 2.5 },
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

    // Node tap handler: highlight neighborhood, center node, update inspector
    cy.on("tap", "node", (evt) => {
      const node = evt.target
      const id = node.id()

      cy.elements().addClass("faded")
      const hood = node.closedNeighborhood()
      hood.removeClass("faded")
      node.addClass("highlight")

      const raw = rawGraph?.nodes.find((n) => n.id === id)
      if (raw) {
        const rawScore = raw.riskScore
        setSelectedNode({
          id: raw.id,
          label: raw.label,
          type: raw.nodeType || "address",
          riskScore:
            rawScore !== undefined && rawScore !== null
              ? Math.round(rawScore > 1 ? rawScore : rawScore * 100)
              : undefined,
          riskLevel: raw.riskLevel,
          behaviorType: raw.behaviorType,
          alerts: raw.alerts || raw.metadata?.alerts,
          metadata: raw.metadata as never,
        })
        setSelectedEdge(null)
      }
    })

    // Edge tap handler: highlight edge, inspect contained flows
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
          totalValueBtc: raw.totalValueBtc || "0",
          transactionCount: raw.transactionCount || 1,
          transactions: raw.transactions || [],
        })
        setSelectedNode(null)
      }
    })

    // Canvas background tap handler: clear highlights
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("faded highlight")
      }
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [elements, rawGraph])

  function zoomBy(factor: number) {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  function fit() {
    cyRef.current?.fit(undefined, 40)
  }

  // Extract structured evidence groups from selected node
  const evidence = useMemo(() => {
    if (!selectedNode?.metadata?.evidence) return null
    return selectedNode.metadata.evidence as {
      graph?: Record<string, any>
      temporal?: Record<string, any>
      network?: Record<string, any>
      ml?: {
        riskScore?: number
        riskLevel?: string
        behaviorClassification?: string
        confidence?: number
        modelId?: string
        topFeatures?: Array<{
          feature_name?: string
          display_label?: string
          direction?: string
          shap_value?: number
          importance_rank?: number
        }>
      }
    }
  }, [selectedNode])

  // Extract alerts for selected node
  const selectedAlerts = useMemo<
    Array<{
      alertId?: string
      alert_id?: string
      alertType?: string
      alert_type?: string
      severity?: string
      priority?: string
      status?: string
      [key: string]: any
    }>
  >(() => {
    if (selectedNode?.alerts && selectedNode.alerts.length > 0) {
      return selectedNode.alerts as any[]
    }
    if (selectedNode?.metadata?.alerts && selectedNode.metadata.alerts.length > 0) {
      return selectedNode.metadata.alerts as any[]
    }
    return []
  }, [selectedNode])

  return (
    <AppLayout title="Graph Explorer">
      <div className={cn("space-y-3 font-sans", isFullscreen && "fixed inset-0 z-50 bg-bg p-4 overflow-hidden")}>
        {/* Top Search, Mode Switcher & Filter Bar */}
        <Panel className="border-line bg-panel shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2.5 p-3.5 text-xs">
            {/* Search Form */}
            <form onSubmit={handleSearchSubmit} className="flex min-w-[300px] flex-1 items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 size-3.5 text-fg-subtle" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Focus Bitcoin address or TXID hash..."
                  className="w-full rounded border border-line bg-panel-2 py-1.5 pl-9 pr-3 text-xs text-fg focus:border-accent focus:bg-panel focus:outline-none transition-colors font-mono placeholder:font-sans"
                />
              </div>
              <button
                type="submit"
                className="rounded border border-accent bg-accent px-4 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors shadow-xs"
              >
                Focus
              </button>
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("")
                    setSearchParams({})
                    if (viewMode === "investigation") {
                      setRawGraph(null)
                      setSelectedNode(null)
                      setSelectedEdge(null)
                    } else {
                      loadGraphData(undefined, currentHops, "full", suspiciousOnly)
                    }
                  }}
                  className="rounded border border-line bg-panel px-2.5 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300"
                >
                  Reset
                </button>
              ) : null}
            </form>

            {/* Mode Switcher: Investigation vs Full Connections */}
            <div className="flex items-center rounded border border-line bg-panel-2 p-0.5">
              <button
                type="button"
                onClick={() => handleModeChange("investigation")}
                className={cn(
                  "flex items-center gap-1.5 rounded px-3 py-1 text-xs font-semibold transition-colors",
                  viewMode === "investigation"
                    ? "bg-accent text-white shadow-xs"
                    : "text-fg-muted hover:text-fg",
                )}
                title="Focused forensic neighborhood around the selected entity"
              >
                <Crosshair className="size-3" />
                Investigation
              </button>
              <button
                type="button"
                onClick={() => handleModeChange("full")}
                className={cn(
                  "flex items-center gap-1.5 rounded px-3 py-1 text-xs font-semibold transition-colors",
                  viewMode === "full"
                    ? "bg-accent text-white shadow-xs"
                    : "text-fg-muted hover:text-fg",
                )}
                title="Broad connection graph for the active dataset"
              >
                <Network className="size-3" />
                Full Connections
              </button>
            </div>

            {/* In Investigation Mode: Hop Depth Selector */}
            {viewMode === "investigation" && (
              <div className="flex items-center gap-1 rounded border border-line bg-panel p-0.5">
                <span className="px-2 font-semibold text-fg-muted uppercase tracking-wider text-[10px] flex items-center gap-1">
                  <GitFork className="size-3" />
                  Depth:
                </span>
                {[1, 2, 3].map((h) => (
                  <button
                    key={h}
                    type="button"
                    onClick={() => handleHopChange(h)}
                    className={cn(
                      "rounded px-2.5 py-1 text-xs font-semibold transition-colors",
                      currentHops === h ? "bg-accent text-white shadow-xs" : "text-fg-muted hover:text-fg",
                    )}
                  >
                    {h}-hop
                  </button>
                ))}
              </div>
            )}

            {/* Utilities & Filters */}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 cursor-pointer text-fg-muted hover:text-fg font-medium">
                <input
                  type="checkbox"
                  checked={suspiciousOnly}
                  onChange={(e) => handleHighRiskToggle(e.target.checked)}
                  className="rounded border-line accent-accent"
                />
                High Risk Only
              </label>

              {suspiciousOnly && (
                <span className="rounded bg-amber-100 text-amber-900 border border-amber-300 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  Risk ≥ 50%
                </span>
              )}

              <button
                type="button"
                onClick={() => {
                  const target = searchQuery.trim() || focusParam || selectedNode?.id
                  loadGraphData(target || undefined, currentHops, viewMode, suspiciousOnly)
                }}
                className="flex items-center gap-1 rounded border border-line bg-panel px-2.5 py-1.5 text-fg-muted hover:text-fg hover:border-gray-300"
                title="Reload current graph data"
              >
                <RefreshCw className="size-3" />
                Reload
              </button>

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="flex items-center gap-1 rounded border border-line bg-panel px-2.5 py-1.5 text-fg-muted hover:text-fg hover:border-gray-300"
                title={isFullscreen ? "Exit Fullscreen" : "Fullscreen View"}
              >
                {isFullscreen ? <Minimize2 className="size-3.5" /> : <Maximize2 className="size-3.5" />}
                {isFullscreen ? "Exit" : "Full"}
              </button>
            </div>
          </div>
        </Panel>

        {/* Compact Investigation Summary Bar */}
        {rawGraph && (
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2 rounded border border-line bg-panel text-xs text-fg-muted shadow-2xs">
            <div className="flex items-center gap-3">
              <span className="font-semibold uppercase tracking-wider text-[10px] text-fg-subtle flex items-center gap-1">
                <Activity className="size-3 text-accent" />
                {viewMode === "investigation"
                  ? `Investigation Mode (${currentHops}-hop neighborhood)`
                  : "Full Connection Mode (Expanded Network)"}
              </span>
              {selectedNode && (
                <span className="flex items-center gap-1 text-[11px] font-mono text-fg bg-panel-2 px-2 py-0.5 rounded border border-line">
                  Target: <span className="font-bold">{selectedNode.label}</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-4 text-[11px]">
              <div className="flex items-center gap-2">
                <span className="text-fg-subtle font-medium uppercase text-[10px]">Connected:</span>
                <span>
                  <strong className="font-mono text-fg">{summaryStats.txCount}</strong> TXs
                </span>
                <span>•</span>
                <span>
                  <strong className="font-mono text-fg">{summaryStats.addrCount}</strong> Addrs
                </span>
                {summaryStats.clusterCount > 0 && (
                  <>
                    <span>•</span>
                    <span>
                      <strong className="font-mono text-fg">{summaryStats.clusterCount}</strong> Clusters
                    </span>
                  </>
                )}
              </div>

              <div className="h-3 w-px bg-line" />

              <div className="flex items-center gap-2">
                <span className="text-fg-subtle font-medium uppercase text-[10px]">Risk Exposure:</span>
                <span className="text-amber-700 font-semibold">
                  <strong className="font-mono">{summaryStats.highRiskCount}</strong> High
                </span>
                <span>•</span>
                <span className="text-red-700 font-semibold">
                  <strong className="font-mono">{summaryStats.criticalRiskCount}</strong> Critical
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Main Workspace: Left 70% Graph Canvas + Right 30% Inspector */}
        <div
          className={cn(
            "flex flex-col lg:flex-row gap-3 rounded border border-line bg-panel overflow-hidden shadow-xs",
            isFullscreen ? "h-[calc(100vh-140px)]" : "h-[740px]",
          )}
        >
          {/* Left ~70%: Graph Canvas Container */}
          <div className="relative flex-1 bg-white overflow-hidden flex flex-col">
            {loading ? (
              <div className="m-auto">
                <LoadingState label="Building transaction neighborhood..." />
              </div>
            ) : errorMsg ? (
              <div className="m-auto p-8 max-w-md text-center space-y-3">
                <div className="size-10 rounded-full bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center mx-auto">
                  <AlertTriangle className="size-5" />
                </div>
                <h4 className="text-sm font-semibold text-fg">Investigation Notice</h4>
                <p className="text-xs text-fg-muted leading-relaxed">{errorMsg}</p>
                {sampleTxid && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery(sampleTxid)
                      setSearchParams({ focus: sampleTxid })
                      loadGraphData(sampleTxid, currentHops, "investigation", suspiciousOnly)
                    }}
                    className="mt-2 text-xs text-accent hover:underline font-medium"
                  >
                    Try sample transaction →
                  </button>
                )}
              </div>
            ) : viewMode === "investigation" && !rawGraph ? (
              /* Initial Empty State in Investigation Mode */
              <div className="m-auto p-8 max-w-lg text-center space-y-4">
                <div className="size-12 rounded-full bg-slate-50 border border-slate-200 text-accent flex items-center justify-center mx-auto shadow-2xs">
                  <Crosshair className="size-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-fg">Graph Explorer Investigation Workspace</h3>
                  <p className="mt-1 text-xs text-fg-muted max-w-sm mx-auto leading-relaxed">
                    Search a Bitcoin transaction or address to begin investigation.
                  </p>
                </div>

                {/* Quick 1-Click Investigation Pills */}
                {(sampleTxid || sampleAddress) && (
                  <div className="pt-3 border-t border-line space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle block">
                      Quick Start from Loaded Dataset
                    </span>
                    <div className="flex flex-col sm:flex-row gap-2 justify-center">
                      {sampleTxid && (
                        <button
                          type="button"
                          onClick={() => {
                            setSearchQuery(sampleTxid)
                            setSearchParams({ focus: sampleTxid })
                            loadGraphData(sampleTxid, currentHops, "investigation", suspiciousOnly)
                          }}
                          className="rounded border border-line bg-panel-2 px-3 py-2 text-left text-xs hover:border-accent hover:bg-panel transition-colors"
                        >
                          <span className="text-[10px] font-semibold text-fg-subtle uppercase block">Sample TXID</span>
                          <span className="font-mono text-fg font-medium">{sampleTxid.slice(0, 16)}…</span>
                        </button>
                      )}
                      {sampleAddress && (
                        <button
                          type="button"
                          onClick={() => {
                            setSearchQuery(sampleAddress)
                            setSearchParams({ focus: sampleAddress })
                            loadGraphData(sampleAddress, currentHops, "investigation", suspiciousOnly)
                          }}
                          className="rounded border border-line bg-panel-2 px-3 py-2 text-left text-xs hover:border-accent hover:bg-panel transition-colors"
                        >
                          <span className="text-[10px] font-semibold text-fg-subtle uppercase block">Sample Address</span>
                          <span className="font-mono text-fg font-medium">{sampleAddress.slice(0, 16)}…</span>
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Active Cytoscape Graph Canvas */
              <div ref={containerRef} className="h-full w-full" />
            )}

            {/* Compact Legend Overlay */}
            {rawGraph && !loading && (
              <div className="absolute bottom-3 left-3 z-10 rounded border border-line bg-white/90 p-2.5 shadow-sm text-[10px] backdrop-blur-xs space-y-1.5 font-sans">
                <div className="font-bold text-fg-subtle uppercase tracking-wider text-[9px]">Entity Legend</div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 font-medium text-fg">
                    <span className="size-2.5 rounded-full bg-[#3B6D9C] inline-block" /> Address
                  </span>
                  <span className="flex items-center gap-1 font-medium text-fg">
                    <span className="size-2.5 rounded-xs bg-[#173B63] inline-block" /> Transaction
                  </span>
                  <span className="flex items-center gap-1 font-medium text-fg">
                    <span className="size-2.5 rotate-45 bg-[#4F46E5] inline-block" /> Cluster
                  </span>
                </div>
                <div className="pt-1 border-t border-line-soft flex items-center gap-2.5 text-fg-muted">
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-[#2F6B4F] inline-block" /> Low
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-[#A46A16] inline-block" /> Med
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-[#B85D1B] inline-block" /> High
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full bg-[#A63D3D] inline-block" /> Crit
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="size-2 rounded-full border-2 border-[#0F172A] inline-block" /> Focus
                  </span>
                </div>
              </div>
            )}

            {/* Canvas Zoom Controls Overlay */}
            {rawGraph && !loading && (
              <div className="absolute bottom-3 right-3 z-10 flex flex-col gap-1 rounded border border-line bg-white/90 p-1 shadow-sm backdrop-blur-xs">
                <button
                  type="button"
                  onClick={() => zoomBy(1.2)}
                  className="rounded p-1 text-fg-muted hover:bg-gray-100 hover:text-fg"
                  title="Zoom in"
                >
                  <Plus className="size-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => zoomBy(0.8)}
                  className="rounded p-1 text-fg-muted hover:bg-gray-100 hover:text-fg"
                  title="Zoom out"
                >
                  <Minus className="size-3.5" />
                </button>
                <button
                  type="button"
                  onClick={fit}
                  className="rounded p-1 text-fg-muted hover:bg-gray-100 hover:text-fg"
                  title="Fit to screen"
                >
                  <Crosshair className="size-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Right ~30%: Forensic Investigation Inspector */}
          {(selectedNode || selectedEdge) && (
            <div className="w-full lg:w-[380px] shrink-0 border-t lg:border-t-0 lg:border-l border-line bg-panel p-4 overflow-y-auto space-y-4 font-sans text-xs shadow-xs">
              {/* Inspector Header */}
              <div className="flex items-start justify-between border-b border-line pb-2.5">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                    <ShieldAlert className="size-3 text-accent" />
                    Investigation Inspector
                  </span>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="rounded bg-slate-100 text-slate-800 border border-slate-300 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                      {selectedNode ? selectedNode.type : "AGGREGATED FLOW"}
                    </span>
                    {selectedNode?.riskLevel ? (
                      <SeverityBadge severity={selectedNode.riskLevel.toLowerCase() as Severity} />
                    ) : null}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedNode(null)
                    setSelectedEdge(null)
                    cyRef.current?.elements().removeClass("faded highlight")
                  }}
                  className="rounded p-1 text-fg-subtle hover:text-fg hover:bg-panel-2 transition-colors"
                  title="Close Inspector"
                >
                  <X className="size-4" />
                </button>
              </div>

              {/* Node Inspector Details */}
              {selectedNode ? (
                <div className="space-y-4">
                  {/* Entity Identifier with Copy Action */}
                  <div className="rounded border border-line bg-panel-2 p-2.5 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                        Entity Identifier
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyIdentifier(selectedNode.id)}
                        className="flex items-center gap-1 text-[11px] font-medium text-accent hover:underline"
                      >
                        {copiedId ? (
                          <>
                            <Check className="size-3 text-green-600" />
                            <span className="text-green-600">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="size-3" />
                            <span>Copy ID</span>
                          </>
                        )}
                      </button>
                    </div>
                    <p className="font-mono text-xs text-fg break-all font-semibold select-all leading-tight">
                      {selectedNode.id}
                    </p>
                  </div>

                  {/* Section 8: Risk Assessment */}
                  {selectedNode.riskScore !== undefined ? (
                    <div className="rounded border border-line bg-panel-2 p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                          Risk Assessment
                        </span>
                        {selectedNode.behaviorType && (
                          <span className="rounded bg-accent/10 text-accent font-semibold px-2 py-0.5 text-[10px] border border-accent/20">
                            {selectedNode.behaviorType}
                          </span>
                        )}
                      </div>

                      <div className="flex items-baseline gap-2">
                        <span
                          className="font-mono text-3xl font-bold tabular-nums"
                          style={{
                            color: severityColorVar(
                              (selectedNode.riskLevel?.toLowerCase() as Severity) || "low",
                            ),
                          }}
                        >
                          {selectedNode.riskScore}%
                        </span>
                        <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">
                          {selectedNode.riskLevel || "standard"}
                        </span>
                      </div>
                      <p className="text-[11px] text-fg-muted">
                        Persisted machine learning behavioral assessment.
                      </p>
                    </div>
                  ) : null}

                  {/* Section 9: Transaction Details OR Section 10: Address Details */}
                  {selectedNode.type === "transaction" ? (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                        <Activity className="size-3" />
                        Transaction Attributes
                      </span>
                      <div className="rounded border border-line divide-y divide-line-soft bg-panel-2 p-2.5 text-xs">
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Total Amount:</span>
                          <span className="font-mono text-fg font-semibold">
                            {selectedNode.metadata?.amountBtc ?? selectedNode.metadata?.totalOutputValueBtc ?? "—"} BTC
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Network Fee:</span>
                          <span className="font-mono text-fg font-medium">
                            {selectedNode.metadata?.feeBtc ?? "—"} BTC
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Inputs / Outputs:</span>
                          <span className="font-mono text-fg font-medium">
                            {selectedNode.metadata?.inputCount ?? 0} in / {selectedNode.metadata?.outputCount ?? 0} out
                          </span>
                        </div>
                        {selectedNode.metadata?.timestamp && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Timestamp:</span>
                            <span className="font-mono text-fg-muted">
                              {formatDateTime(selectedNode.metadata.timestamp)}
                            </span>
                          </div>
                        )}
                        {selectedNode.metadata?.blockHeight && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Block Height:</span>
                            <span className="font-mono text-fg-muted">{selectedNode.metadata.blockHeight}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                        <Layers className="size-3" />
                        Address Attributes
                      </span>
                      <div className="rounded border border-line divide-y divide-line-soft bg-panel-2 p-2.5 text-xs">
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Transactions:</span>
                          <span className="font-mono text-fg font-semibold">
                            {selectedNode.metadata?.transactionCount ?? 1}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Total Received:</span>
                          <span className="font-mono text-fg font-medium">
                            {selectedNode.metadata?.totalReceivedBtc ?? "0.00000000"} BTC
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Total Sent:</span>
                          <span className="font-mono text-fg font-medium">
                            {selectedNode.metadata?.totalSentBtc ?? "0.00000000"} BTC
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Risk Exposure:</span>
                          <span className="font-mono font-semibold uppercase text-fg">
                            {selectedNode.metadata?.riskExposure || selectedNode.riskLevel || "Low"}
                          </span>
                        </div>
                        <div className="flex justify-between py-1">
                          <span className="text-fg-muted">Cluster ID:</span>
                          <span className="font-mono text-fg-muted">
                            {selectedNode.metadata?.clusterId || "—"}
                          </span>
                        </div>
                        {selectedNode.metadata?.activeDays !== undefined && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Active Days:</span>
                            <span className="font-mono text-fg-muted">{selectedNode.metadata.activeDays} days</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Section 11: Graph Evidence */}
                  {evidence?.graph && Object.keys(evidence.graph).some((k) => evidence.graph?.[k] !== undefined && evidence.graph?.[k] !== null) && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                        <Network className="size-3" />
                        Graph Evidence
                      </span>
                      <div className="rounded border border-line divide-y divide-line-soft bg-panel-2 p-2.5 text-xs">
                        {evidence.graph.fanIn !== undefined && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Fan-in:</span>
                            <span className="font-mono text-fg font-semibold">{evidence.graph.fanIn}</span>
                          </div>
                        )}
                        {evidence.graph.fanOut !== undefined && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Fan-out:</span>
                            <span className="font-mono text-fg font-semibold">{evidence.graph.fanOut}</span>
                          </div>
                        )}
                        {evidence.graph.componentSize !== undefined && evidence.graph.componentSize !== null && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Component Size:</span>
                            <span className="font-mono text-fg font-medium">{evidence.graph.componentSize}</span>
                          </div>
                        )}
                        {evidence.graph.addressReuse !== undefined && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Address Reuse:</span>
                            <span className="font-mono text-fg font-medium">
                              {String(evidence.graph.addressReuse)}
                            </span>
                          </div>
                        )}
                        {evidence.graph.clusterId && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Cluster Size:</span>
                            <span className="font-mono text-fg font-medium">{evidence.graph.clusterId}</span>
                          </div>
                        )}
                        {evidence.graph.neighborCount !== undefined && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Neighbor Count:</span>
                            <span className="font-mono text-fg font-medium">{evidence.graph.neighborCount}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Section 12: Temporal Evidence */}
                  {evidence?.temporal && Object.keys(evidence.temporal).some((k) => evidence.temporal?.[k] !== undefined && evidence.temporal?.[k] !== null) && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                        <Clock className="size-3" />
                        Temporal Evidence
                      </span>
                      <div className="rounded border border-line divide-y divide-line-soft bg-panel-2 p-2.5 text-xs">
                        {evidence.temporal.txInLast1m !== undefined && evidence.temporal.txInLast1m !== null && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">TXs in Last 1m:</span>
                            <span className="font-mono text-fg font-semibold">{evidence.temporal.txInLast1m}</span>
                          </div>
                        )}
                        {evidence.temporal.txInLast5m !== undefined && evidence.temporal.txInLast5m !== null && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">TXs in Last 5m:</span>
                            <span className="font-mono text-fg font-semibold">{evidence.temporal.txInLast5m}</span>
                          </div>
                        )}
                        {evidence.temporal.timeSincePrevTx !== undefined && evidence.temporal.timeSincePrevTx !== null && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Latency Since Prev TX:</span>
                            <span className="font-mono text-fg font-medium">
                              {evidence.temporal.timeSincePrevTx}s
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Section 13: Network Evidence */}
                  {evidence?.network && Object.keys(evidence.network).some((k) => evidence.network?.[k] !== undefined && evidence.network?.[k] !== null) && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                        <Activity className="size-3" />
                        Network Evidence
                      </span>
                      <div className="rounded border border-line divide-y divide-line-soft bg-panel-2 p-2.5 text-xs">
                        {evidence.network.country && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Country:</span>
                            <span className="font-mono text-fg font-semibold">{evidence.network.country}</span>
                          </div>
                        )}
                        {evidence.network.asn && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">ASN:</span>
                            <span className="font-mono text-fg font-semibold">AS{evidence.network.asn}</span>
                          </div>
                        )}
                        {evidence.network.srcIp && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Source IP:</span>
                            <span className="font-mono text-fg font-medium">{evidence.network.srcIp}</span>
                          </div>
                        )}
                        {evidence.network.srcPort && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Source Port:</span>
                            <span className="font-mono text-fg-muted">{evidence.network.srcPort}</span>
                          </div>
                        )}
                        {evidence.network.dstPort && (
                          <div className="flex justify-between py-1">
                            <span className="text-fg-muted">Destination Port:</span>
                            <span className="font-mono text-fg-muted">{evidence.network.dstPort}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Section 14: Model Evidence & Top 5 SHAP Explanations */}
                  {evidence?.ml?.topFeatures && evidence.ml.topFeatures.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                          <Cpu className="size-3 text-accent" />
                          Model Evidence
                        </span>
                        {evidence.ml.modelId && (
                          <span className="text-[10px] font-mono text-fg-subtle">
                            {evidence.ml.modelId}
                          </span>
                        )}
                      </div>

                      <div className="rounded border border-line bg-panel-2 p-2.5 space-y-2">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted block">
                          Top Contributing Factors (SHAP Attribution)
                        </span>
                        <div className="space-y-1.5">
                          {evidence.ml.topFeatures.slice(0, 5).map((f, idx) => (
                            <div
                              key={f.feature_name || idx}
                              className="flex items-center justify-between rounded border border-line bg-panel p-1.5 text-[11px]"
                            >
                              <div className="min-w-0 pr-2">
                                <span className="font-bold text-fg-subtle mr-1.5">#{idx + 1}</span>
                                <span className="font-mono font-medium text-fg truncate">
                                  {f.display_label || f.feature_name}
                                </span>
                              </div>
                              <span
                                className={cn(
                                  "shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                                  f.direction === "increases_risk"
                                    ? "bg-red-50 text-red-700 border border-red-200"
                                    : "bg-green-50 text-green-700 border border-green-200",
                                )}
                              >
                                {f.direction === "increases_risk" ? "+ Risk" : "- Risk"}
                              </span>
                            </div>
                          ))}
                        </div>
                        <p className="text-[10px] text-fg-subtle italic pt-1 border-t border-line-soft">
                          Model evidence — not proof of illicit activity.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Section 15: Alert Connection */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1">
                      <AlertTriangle className="size-3 text-amber-600" />
                      Persistent Alerts
                    </span>

                    {selectedAlerts.length > 0 ? (
                      <div className="space-y-2">
                        {selectedAlerts.map((a: any) => (
                          <div
                            key={a.alertId || a.alert_id || Math.random().toString()}
                            className="rounded border border-amber-300 bg-amber-50/50 p-2.5 space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-bold text-amber-900 text-[11px]">
                                {a.alertId || a.alert_id}
                              </span>
                              <SeverityBadge severity={(a.severity?.toLowerCase() as Severity) || "high"} />
                            </div>
                            <div className="flex items-center justify-between text-[10px] text-fg-muted">
                              <span>Type: <strong className="text-fg">{a.alertType || a.alert_type || "SUSPICIOUS_FLOW"}</strong></span>
                              <span>Priority: <strong className="text-fg">{a.priority || "P1"}</strong></span>
                              <span>Status: <strong className="text-fg">{a.status || "NEW"}</strong></span>
                            </div>
                            <button
                              type="button"
                              onClick={() => navigate("/alerts")}
                              className="w-full mt-1 rounded border border-amber-400 bg-white py-1 text-[11px] font-semibold text-amber-900 hover:bg-amber-100 transition-colors flex items-center justify-center gap-1"
                            >
                              Open in Alert Center <ExternalLink className="size-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded border border-line bg-panel-2 p-2.5 text-center text-fg-subtle text-[11px]">
                        No active alerts linked to this entity.
                      </div>
                    )}
                  </div>

                  {/* Section 16: Investigative Actions */}
                  <div className="space-y-2 pt-3 border-t border-line">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle block">
                      Forensic Actions
                    </span>

                    <div className="grid grid-cols-1 gap-1.5">
                      {/* View Transaction (only for transaction entities) */}
                      {selectedNode.type === "transaction" && (
                        <button
                          type="button"
                          onClick={() => navigate(`/transaction/${selectedNode.id}`)}
                          className="w-full rounded border border-line bg-panel py-2 text-xs font-semibold text-fg hover:border-accent hover:text-accent transition-colors flex items-center justify-center gap-1.5"
                        >
                          <Activity className="size-3.5" />
                          View Full Transaction Record
                        </button>
                      )}

                      {/* View Alert (only if alert exists) */}
                      {selectedAlerts.length > 0 && (
                        <button
                          type="button"
                          onClick={() => navigate("/alerts")}
                          className="w-full rounded border border-amber-300 bg-amber-50 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-100 transition-colors flex items-center justify-center gap-1.5"
                        >
                          <AlertTriangle className="size-3.5" />
                          View Linked Alert Dossier ({selectedAlerts.length})
                        </button>
                      )}

                      {/* Investigate in Detail */}
                      <button
                        type="button"
                        onClick={() =>
                          navigate(
                            `/investigation/${selectedNode.id}?entityType=${selectedNode.type}`,
                          )
                        }
                        className="w-full rounded border border-accent bg-accent py-2 text-xs font-semibold text-white hover:bg-accent/90 transition-colors shadow-xs flex items-center justify-center gap-1.5"
                      >
                        <ShieldAlert className="size-3.5" />
                        Open Deep Forensic Investigation
                      </button>

                      {/* In Investigation Mode: Hop Expansion */}
                      {viewMode === "investigation" && (
                        <button
                          type="button"
                          onClick={() => handleHopChange(currentHops >= 3 ? 1 : currentHops + 1)}
                          className="w-full rounded border border-line bg-panel-2 py-1.5 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 transition-colors flex items-center justify-center gap-1"
                        >
                          <GitFork className="size-3" />
                          Expand Neighborhood (+1 Hop)
                        </button>
                      )}

                      {/* Switch to Full Connections View */}
                      {viewMode === "investigation" && (
                        <button
                          type="button"
                          onClick={() => handleModeChange("full")}
                          className="w-full rounded border border-dashed border-line bg-panel py-1.5 text-[11px] font-medium text-fg-subtle hover:text-fg hover:border-fg-muted transition-colors flex items-center justify-center gap-1"
                        >
                          <Network className="size-3" />
                          Expand to Full Connections View
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ) : selectedEdge ? (
                /* Selected Edge Inspector */
                <div className="space-y-4">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                      Aggregated Flow Value
                    </span>
                    <p className="mt-1 font-mono text-2xl font-bold text-fg">
                      {selectedEdge.totalValueBtc} BTC
                    </p>
                    <p className="text-xs text-fg-muted mt-0.5">
                      {selectedEdge.transactionCount} transaction
                      {selectedEdge.transactionCount === 1 ? "" : "s"} aggregated
                    </p>
                  </div>

                  <div className="space-y-2 text-xs rounded border border-line bg-panel-2 p-3">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                        Source
                      </span>
                      <MonoId value={selectedEdge.source} head={10} tail={8} className="mt-0.5 block" />
                    </div>
                    <div className="pt-2 border-t border-line-soft">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                        Target
                      </span>
                      <MonoId value={selectedEdge.target} head={10} tail={8} className="mt-0.5 block" />
                    </div>
                  </div>

                  {selectedEdge.transactions && selectedEdge.transactions.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                        Contained Transactions ({selectedEdge.transactions.length})
                      </span>
                      <div className="max-h-56 space-y-1.5 overflow-y-auto">
                        {selectedEdge.transactions.map((t) => (
                          <div
                            key={t.transactionId}
                            onClick={() =>
                              navigate(`/investigation/${t.transactionId}?entityType=transaction`)
                            }
                            className="cursor-pointer rounded border border-line bg-panel p-2 hover:border-accent transition-colors"
                          >
                            <MonoId value={t.transactionId} head={8} tail={6} copyable={false} />
                            <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
                              <span className="font-semibold text-fg">{t.valueBtc} BTC</span>
                              <span className="font-mono text-fg-subtle">
                                {t.timestamp ? formatDateTime(t.timestamp) : "—"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
