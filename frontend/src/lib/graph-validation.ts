import type { ElementDefinition } from "cytoscape"
import type { GraphExport, GraphNodeDto, GraphEdgeDto } from "@/api/types"

// Institutional forensic palette
export const typeColors: Record<string, string> = {
  wallet: "#3B6D9C",
  address: "#3B6D9C",
  transaction: "#173B63",
  cluster: "#4F46E5",
  ip: "#A46A16",
  network: "#A46A16",
  exchange: "#2F6B4F",
  mixer: "#A63D3D",
}

export const severityColors: Record<string, string> = {
  low: "#2F6B4F",
  medium: "#A46A16",
  high: "#B85D1B",
  critical: "#A63D3D",
}

export interface BuildValidatedCytoscapeElementsOptions {
  rawGraph?: GraphExport | null
  suspiciousOnly?: boolean
  viewMode?: "investigation" | "full" | string
  focusedId?: string
}

export interface ValidatedGraphElements {
  nodes: ElementDefinition[]
  edges: ElementDefinition[]
}

/**
 * Validates, deduplicates, and constructs safe Cytoscape elements.
 * 
 * Ensures:
 * - No null or undefined elements
 * - Unique node and edge IDs
 * - Valid edge source and target references that exist in the validated node set
 * - Safe color and shape mapping
 * - High-risk-only filtering without breaking Cytoscape topology
 */
export function buildValidatedCytoscapeElements(
  options: BuildValidatedCytoscapeElementsOptions
): ValidatedGraphElements {
  const { rawGraph, suspiciousOnly = false, focusedId } = options

  if (!rawGraph || !Array.isArray(rawGraph.nodes) || !Array.isArray(rawGraph.edges)) {
    return { nodes: [], edges: [] }
  }

  const validNodeIds = new Set<string>()
  const usedElementIds = new Set<string>()
  const nodes: ElementDefinition[] = []

  const targetFocus = (focusedId || "").trim().toLowerCase()

  for (const n of rawGraph.nodes) {
    if (!n || typeof n !== "object" || !n.id || typeof n.id !== "string") {
      continue
    }

    const trimmedId = n.id.trim()
    if (!trimmedId || usedElementIds.has(trimmedId)) {
      continue
    }

    const nType = (n.nodeType || "address").toLowerCase()
    const lvl = (n.riskLevel || "").toLowerCase()
    const rawScore = n.riskScore ?? 0
    const score = typeof rawScore === "number" && rawScore > 1 ? rawScore / 100 : rawScore
    const isHighRisk = lvl === "high" || lvl === "critical" || (typeof score === "number" && score >= 0.50)

    // Enforce high-risk filter if active (risk_score >= 0.50 or high/critical)
    if (suspiciousOnly && !isHighRisk) {
      continue
    }

    usedElementIds.add(trimmedId)
    validNodeIds.add(trimmedId)

    // Color mapping with restrained semantic emphasis
    let nodeColor = "#64748B" // Neutral / default fallback
    const hasRisk = (n.riskLevel && n.riskLevel.trim() !== "") || (n.riskScore !== undefined && n.riskScore !== null)
    if (hasRisk) {
      if (lvl === "critical" || (score !== null && score >= 0.80)) {
        nodeColor = severityColors.critical
      } else if (lvl === "high" || (score !== null && score >= 0.50)) {
        nodeColor = severityColors.high
      } else if (lvl === "medium" || (score !== null && score >= 0.25)) {
        nodeColor = severityColors.medium
      } else {
        nodeColor = severityColors.low
      }
    } else if (typeColors[nType]) {
      nodeColor = typeColors[nType]
    }

    const borderColor =
      nType === "transaction" ? "#0F172A" : nType === "cluster" ? "#312E81" : "#1E3A8A"

    const displayLabel = n.label || (trimmedId.length > 12 ? `${trimmedId.slice(0, 8)}…` : trimmedId)
    const isFocus = Boolean(
      targetFocus &&
        (trimmedId.toLowerCase() === targetFocus || (n.label && n.label.toLowerCase() === targetFocus))
    )

    nodes.push({
      data: {
        id: trimmedId,
        label: displayLabel,
        nodeType: nType,
        riskScore: n.riskScore,
        riskLevel: n.riskLevel,
        color: nodeColor,
        borderColor: borderColor,
        shape: nType === "transaction" ? "round-rectangle" : nType === "cluster" ? "hexagon" : "ellipse",
        isFocus: isFocus ? 1 : 0,
        isSelected: 0,
      },
    })
  }

  const edges: ElementDefinition[] = []

  for (const e of rawGraph.edges) {
    if (!e || typeof e !== "object" || !e.id || typeof e.id !== "string") {
      continue
    }

    const trimmedEdgeId = e.id.trim()
    const trimmedSource = typeof e.source === "string" ? e.source.trim() : ""
    const trimmedTarget = typeof e.target === "string" ? e.target.trim() : ""

    if (!trimmedEdgeId || !trimmedSource || !trimmedTarget) {
      continue
    }

    // Cytoscape requires edge source and target nodes to be present in elements
    if (!validNodeIds.has(trimmedSource) || !validNodeIds.has(trimmedTarget)) {
      continue
    }

    // Prevent duplicate element IDs (Cytoscape shares ID namespace across nodes and edges)
    if (usedElementIds.has(trimmedEdgeId)) {
      continue
    }

    usedElementIds.add(trimmedEdgeId)

    const valBtc = parseFloat(e.totalValueBtc || "0")
    const isSuspicious = (e.totalValueSatoshi || 0) > 100_000_000 || valBtc >= 1.0

    edges.push({
      data: {
        id: trimmedEdgeId,
        source: trimmedSource,
        target: trimmedTarget,
        label: valBtc > 0 ? `${valBtc.toFixed(3)} BTC` : "",
        totalValueBtc: e.totalValueBtc,
        transactionCount: e.transactionCount,
        transactions: e.transactions || [],
        suspicious: isSuspicious ? 1 : 0,
      },
    })
  }

  return { nodes, edges }
}
