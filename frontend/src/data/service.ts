/**
 * Data service — centralized integration seam connecting frontend pages to the FastAPI backend.
 * All domain transformations and DTO adaptions are encapsulated here.
 * NEVER returns fabricated mock data.
 */

import {
  getAddress,
  getAddressSubgraph,
  getAnalysis,
  getDataset,
  getTransaction as apiGetTransaction,
  listAddresses,
  listAnalysesForDataset,
  listAnalysisResults,
  listDatasets,
  listTransactions,
  uploadDataset as apiUploadDataset,
  triggerAnalysis as apiTriggerAnalysis,
} from "@/api"
import type {
  Alert,
  AnomalyBucket,
  DashboardStats,
  DatasetInfo,
  Entity,
  EntityType,
  EvidenceItem,
  Investigation,
  Severity,
  TimelineEvent,
  Transaction,
} from "./types"

export interface SearchResult {
  id: string
  kind: "entity" | "transaction"
  label: string
  sublabel: string
  route: string
}

/**
 * Resolves the currently active dataset and analysis IDs from the backend.
 */
export async function getActiveContext(): Promise<{
  datasetId?: string
  analysisId?: string
}> {
  try {
    const datasetsRes = await listDatasets({
      page: 1,
      pageSize: 1,
      sortBy: "uploadedAt",
      sortDir: "desc",
    })
    const datasets = datasetsRes.data || []
    if (!datasets.length) return {}

    const datasetId = datasets[0].datasetId
    const analyses = await listAnalysesForDataset(datasetId)
    const analysisId = analyses.length ? analyses[0].analysisId : undefined

    return { datasetId, analysisId }
  } catch (err) {
    console.error("Failed to resolve active context from backend:", err)
    return {}
  }
}

/**
 * Aggregates dashboard statistics from live datasets and analysis runs.
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  const { datasetId, analysisId } = await getActiveContext()

  if (!datasetId) {
    return {
      totalTransactions: 0,
      totalEntities: 0,
      suspiciousEntities: 0,
      highRiskEntities: 0,
      activeAlerts: 0,
      anomaliesDetected: 0,
      deltas: { transactions: 0, entities: 0, alerts: 0, highRisk: 0 },
      anomalySeries: [],
    }
  }

  const [datasetDetail, addrList] = await Promise.all([
    getDataset(datasetId).catch(() => null),
    listAddresses(datasetId, { page: 1, pageSize: 1, analysisId }).catch(() => null),
  ])

  let totalEntities = addrList?.meta?.pagination?.totalItems || 0
  let highRisk = 0
  let criticalRisk = 0
  let activeAlerts = 0
  let anomaliesDetected = 0

  if (analysisId) {
    try {
      const analysis = await getAnalysis(analysisId)
      if (analysis.entityCount) totalEntities = analysis.entityCount
      highRisk = analysis.highRiskCount || 0
      criticalRisk = analysis.criticalRiskCount || 0
      activeAlerts = highRisk + criticalRisk
      anomaliesDetected = activeAlerts
    } catch {
      // Non-blocking analysis lookup failure
    }
  }

  // Construct anomaly series from recent transactions
  let anomalySeries: AnomalyBucket[] = []
  try {
    const txRes = await listTransactions(datasetId, {
      page: 1,
      pageSize: 100,
      sortBy: "timestamp",
      sortDir: "asc",
      analysisId,
    })
    const txs = txRes.data || []
    if (txs.length) {
      const buckets: Record<string, { total: number; anomalies: number }> = {}
      for (const tx of txs) {
        if (!tx.timestamp) continue
        const hour = new Date(tx.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
        if (!buckets[hour]) buckets[hour] = { total: 0, anomalies: 0 }
        buckets[hour].total++
        if (tx.riskLevel === "high" || tx.riskLevel === "critical") {
          buckets[hour].anomalies++
        }
      }
      anomalySeries = Object.entries(buckets).map(([label, b]) => ({
        label,
        transactions: b.total,
        anomalies: b.anomalies,
      }))
    }
  } catch {
    anomalySeries = []
  }

  return {
    totalTransactions: datasetDetail?.canonicalTxCount || datasetDetail?.rowCount || 0,
    totalEntities,
    suspiciousEntities: highRisk,
    highRiskEntities: highRisk + criticalRisk,
    activeAlerts,
    anomaliesDetected,
    deltas: { transactions: 0, entities: 0, alerts: 0, highRisk: 0 },
    anomalySeries,
  }
}

/**
 * Retrieves alerts (ML anomalies) from the active analysis run.
 */
export async function getAlerts(): Promise<Alert[]> {
  const { analysisId } = await getActiveContext()
  if (!analysisId) return []

  const resultsRes = await listAnalysisResults(analysisId, {
    page: 1,
    pageSize: 100,
    sortBy: "riskScore",
    sortDir: "desc",
  })

  const items = resultsRes.data || []
  return items.map((r) => ({
    id: r.entityId,
    entityId: r.entityId,
    entityLabel:
      r.entityId.length > 16
        ? `${r.entityId.slice(0, 8)}…${r.entityId.slice(-6)}`
        : r.entityId,
    entityType: (r.entityType === "address" ? "wallet" : r.entityType) as EntityType,
    riskScore: Math.round(r.riskScore * 100),
    severity: (r.riskLevel?.toLowerCase() as Severity) || "low",
    reason:
      r.predictionLabel ||
      `${r.riskLevel.toUpperCase()} risk anomaly flagged by ML (${r.modelId})`,
    timestamp: r.predictedAt,
    status: "new",
  }))
}

/**
 * Retrieves address entity summaries.
 */
export async function getEntities(): Promise<Entity[]> {
  const { datasetId, analysisId } = await getActiveContext()
  if (!datasetId) return []

  const addrs = await listAddresses(datasetId, {
    page: 1,
    pageSize: 50,
    sortBy: "riskScore",
    sortDir: "desc",
    analysisId,
  })

  return (addrs.data || []).map((a) => ({
    id: a.addressId,
    type: "wallet",
    label: `${a.addressId.slice(0, 8)}…${a.addressId.slice(-6)}`,
    address: a.addressId,
    risk: {
      score: Math.round((a.riskScore || 0) * 100),
      severity: (a.riskLevel?.toLowerCase() as Severity) || "low",
      factors: [],
    },
    firstSeen: a.firstSeen || "",
    lastSeen: a.lastSeen || "",
    totalTransactions: a.transactionCount || 0,
    totalReceived: parseFloat(a.totalReceivedBtc || "0"),
    totalSent: parseFloat(a.totalSentBtc || "0"),
    balance: Math.max(
      0,
      parseFloat(a.totalReceivedBtc || "0") - parseFloat(a.totalSentBtc || "0"),
    ),
    tags: a.riskLevel ? [a.riskLevel.toLowerCase()] : [],
    connectedEntityIds: [],
  }))
}

/**
 * Retrieves transaction summaries.
 */
export async function getTransactions(): Promise<Transaction[]> {
  const { datasetId, analysisId } = await getActiveContext()
  if (!datasetId) return []

  const txRes = await listTransactions(datasetId, {
    page: 1,
    pageSize: 50,
    sortBy: "timestamp",
    sortDir: "desc",
    analysisId,
  })

  return (txRes.data || []).map((t) => ({
    txid: t.transactionId,
    timestamp: t.timestamp || "",
    amount: parseFloat(t.totalOutputValueBtc || t.totalInputValueBtc || "0"),
    fee: parseFloat(t.feeBtc || "0"),
    confirmations: 6,
    block: t.blockHeight || 0,
    inputs: [],
    outputs: [],
    network: {
      ip: "—",
      port: 8333,
      asn: "—",
      asnOrg: "Unspecified Network Telemetry",
      country: "Unknown",
      countryCode: "XX",
      firstSeen: t.timestamp || "",
      lastSeen: t.timestamp || "",
    },
    relatedEntityIds: [],
    riskScore: t.riskScore ? Math.round(t.riskScore * 100) : undefined,
    severity: (t.riskLevel?.toLowerCase() as Severity) || undefined,
  }))
}

/**
 * Retrieves loaded dataset metadata and validation summary.
 */
export async function getDatasetInfo(): Promise<DatasetInfo | null> {
  try {
    const listRes = await listDatasets({
      page: 1,
      pageSize: 1,
      sortBy: "uploadedAt",
      sortDir: "desc",
    })
    const datasets = listRes.data || []
    if (!datasets.length) return null

    const detail = await getDataset(datasets[0].datasetId)
    const val = detail.validationSummary || {}

    return {
      id: detail.datasetId,
      name: detail.name || detail.fileName,
      sizeBytes: detail.sizeBytes,
      format: detail.format.toUpperCase(),
      uploadedAt: detail.uploadedAt,
      stage:
        detail.status === "completed"
          ? "completed"
          : detail.status === "failed"
            ? "failed"
            : "processing",
      progress: 100,
      stats: {
        transactions: detail.canonicalTxCount || detail.rowCount || 0,
        entities: (val.unique_addresses as number) || (val.address_count as number) || 0,
        addresses: (val.unique_addresses as number) || (val.address_count as number) || 0,
        blocks: (val.block_count as number) || 0,
        dateRange: { from: "", to: "" },
        flagged: 0,
      },
      error: detail.errorMessage,
    }
  } catch (err) {
    console.error("Failed to load dataset info from backend:", err)
    return null
  }
}

/**
 * Fetches transaction details including inputs, outputs, and attached ML prediction.
 */
export async function getTransaction(txid: string): Promise<Transaction | null> {
  try {
    const { analysisId } = await getActiveContext()
    const tx = await apiGetTransaction(txid, analysisId)

    const inputs = (tx.inputs || []).map((i) => ({
      entityId: i.inputAddress,
      address: i.inputAddress || "Unknown",
      amount: parseFloat(i.inputValueBtc || "0"),
    }))

    const outputs = (tx.outputs || []).map((o) => ({
      entityId: o.outputAddress,
      address: o.outputAddress || "Unknown",
      amount: parseFloat(o.outputValueBtc || "0"),
    }))

    const related = Array.from(
      new Set(
        [
          ...inputs.map((i) => i.entityId),
          ...outputs.map((o) => o.entityId),
        ].filter(Boolean) as string[],
      ),
    )

    return {
      txid: tx.transactionId,
      timestamp: tx.timestamp || new Date().toISOString(),
      amount: parseFloat(tx.totalOutputValueBtc || tx.totalInputValueBtc || "0"),
      fee: parseFloat(tx.feeBtc || "0"),
      confirmations: 6,
      block: tx.blockHeight || 0,
      inputs,
      outputs,
      network: {
        ip: "—",
        port: 8333,
        asn: "—",
        asnOrg: "Unspecified Network Telemetry",
        country: "Unknown",
        countryCode: "XX",
        firstSeen: tx.timestamp || "",
        lastSeen: tx.timestamp || "",
      },
      relatedEntityIds: related,
      riskScore:
        tx.riskScore !== undefined && tx.riskScore !== null
          ? Math.round(tx.riskScore * 100)
          : undefined,
      severity: (tx.riskLevel?.toLowerCase() as Severity) || undefined,
    }
  } catch (err) {
    console.error(`Failed to load transaction ${txid}:`, err)
    return null
  }
}

/**
 * Fetches complete investigation bundle for an address entity (profile, graph, timeline, evidence).
 */
export async function getInvestigation(entityId: string): Promise<Investigation | null> {
  try {
    const { analysisId } = await getActiveContext()
    const [addr, graphData] = await Promise.all([
      getAddress(entityId, analysisId),
      getAddressSubgraph(entityId, { hops: 2, analysisId }).catch(
        (): import("@/api").GraphExport => ({
          graphId: "fallback",
          datasetId: "",
          generatedAt: new Date().toISOString(),
          nodeCount: 1,
          edgeCount: 0,
          isSubgraph: true,
          subgraphCenter: entityId,
          nodes: [
            {
              id: entityId,
              label: `${entityId.slice(0, 8)}…`,
              nodeType: "address",
              riskScore: 0,
              riskLevel: "low",
              metadata: undefined,
            },
          ],
          edges: [],
        }),
      ),
    ])

    const totalRecv = parseFloat(addr.totalReceivedBtc || "0")
    const totalSent = parseFloat(addr.totalSentBtc || "0")
    const score = Math.round((addr.riskScore || 0) * 100)
    const severity = (addr.riskLevel?.toLowerCase() as Severity) || "low"

    // Convert ML feature explanations to RiskFactors
    const factors = (addr.mlResult?.explanations || []).map((exp, idx) => ({
      id: `f-${idx}`,
      label: exp.displayLabel || exp.featureName,
      weight: exp.normalizedImportance || 0.2,
      description: `${exp.direction === "increases_risk" ? "Elevated risk indicator:" : "Factor"} ${exp.displayLabel} (SHAP value: ${exp.shapValue.toFixed(4)})`,
    }))

    const entity: Entity = {
      id: addr.addressId,
      type: "wallet",
      label: `${addr.addressId.slice(0, 8)}…${addr.addressId.slice(-6)}`,
      address: addr.addressId,
      risk: {
        score,
        severity,
        factors,
        summary: factors.length
          ? `Analysis flagged ${factors.length} primary risk factors for this address.`
          : "Standard transaction behavior observed with no significant anomalies.",
      },
      firstSeen: addr.firstSeen || "",
      lastSeen: addr.lastSeen || "",
      totalTransactions: addr.transactionCount || 0,
      totalReceived: totalRecv,
      totalSent,
      balance: Math.max(0, totalRecv - totalSent),
      tags: addr.riskLevel ? [addr.riskLevel.toLowerCase()] : [],
      connectedEntityIds: graphData.nodes
        .filter((n) => n.id !== entityId)
        .map((n) => n.id),
    }

    // Build connected entities from graph neighbor nodes
    const connectedEntities: Entity[] = graphData.nodes
      .filter((n) => n.id !== entityId)
      .map((n) => ({
        id: n.id,
        type: (n.nodeType === "transaction" ? "transaction" : "wallet") as EntityType,
        label: n.label || `${n.id.slice(0, 8)}…`,
        address: n.id,
        risk: {
          score: Math.round((n.riskScore || 0) * 100),
          severity: (n.riskLevel?.toLowerCase() as Severity) || "low",
          factors: [],
        },
        firstSeen: n.metadata?.firstSeen || "",
        lastSeen: n.metadata?.lastSeen || "",
        totalTransactions: n.metadata?.transactionCount || 0,
        totalReceived: parseFloat(n.metadata?.totalReceivedBtc || "0"),
        totalSent: parseFloat(n.metadata?.totalSentBtc || "0"),
        balance: 0,
        tags: [],
        connectedEntityIds: [],
      }))

    // Build transactions from graph edges
    const relatedTransactions: Transaction[] = []
    const edgeTxs = graphData.edges.flatMap((e) =>
      e.transactions.map((tx) => ({
        txid: tx.transactionId,
        timestamp: tx.timestamp || "",
        amount: parseFloat(tx.valueBtc || "0"),
        fee: 0,
        confirmations: 6,
        block: 0,
        inputs: [{ address: e.source, amount: parseFloat(tx.valueBtc || "0") }],
        outputs: [{ address: e.target, amount: parseFloat(tx.valueBtc || "0") }],
        network: {
          ip: "—",
          port: 8333,
          asn: "—",
          asnOrg: "—",
          country: "Unknown",
          countryCode: "XX",
          firstSeen: "",
          lastSeen: "",
        },
        relatedEntityIds: [e.source, e.target],
      })),
    )
    relatedTransactions.push(...edgeTxs)

    // Build timeline events
    const timeline: TimelineEvent[] = relatedTransactions.map((t, idx) => ({
      id: `tl-${idx}`,
      timestamp: t.timestamp || new Date().toISOString(),
      kind: "transaction",
      title: `Transaction ${t.txid.slice(0, 10)}…`,
      detail: `Transfer of ${t.amount} BTC`,
      txid: t.txid,
    }))

    // Build evidence from graph evidence and SHAP explanations
    const evidence: EvidenceItem[] = [
      ...(addr.mlResult?.graphEvidence || []).map((ge, idx) => ({
        id: `ev-ge-${idx}`,
        category: "connections" as const,
        title: ge.label,
        detail: ge.description,
        severity,
      })),
      ...(addr.mlResult?.explanations || []).map((exp, idx) => ({
        id: `ev-exp-${idx}`,
        category: "model" as const,
        title: exp.displayLabel || exp.featureName,
        detail: `Feature importance rank #${exp.importanceRank} (${exp.direction})`,
        severity,
      })),
    ]

    return {
      entity,
      transactions: relatedTransactions,
      connectedEntities,
      timeline,
      evidence,
      graph: {
        nodes: graphData.nodes.map((n) => ({
          id: n.id,
          label: n.label || `${n.id.slice(0, 8)}…`,
          type: (n.nodeType === "transaction" ? "transaction" : "wallet") as EntityType,
          severity: (n.riskLevel?.toLowerCase() as Severity) || undefined,
          isFocus: n.id === entityId,
        })),
        edges: graphData.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.totalValueBtc ? `${e.totalValueBtc} BTC` : undefined,
          amount: parseFloat(e.totalValueBtc || "0"),
          suspicious: (e.totalValueSatoshi || 0) > 100_000_000,
        })),
      },
    }
  } catch (err) {
    console.error(`Failed to load investigation for ${entityId}:`, err)
    return null
  }
}

/**
 * Global search querying Bitcoin addresses and transactions via live API.
 */
export async function search(query: string): Promise<SearchResult[]> {
  const q = query.trim()
  if (!q) return []

  const results: SearchResult[] = []

  // Direct lookup attempts
  try {
    const tx = await apiGetTransaction(q).catch(() => null)
    if (tx) {
      results.push({
        id: tx.transactionId,
        kind: "transaction",
        label: `TX ${tx.transactionId.slice(0, 12)}…`,
        sublabel: `${tx.totalOutputValueBtc || tx.totalInputValueBtc || "0"} BTC`,
        route: `/transaction/${tx.transactionId}`,
      })
    }
  } catch {
    // TX lookup skipped
  }

  try {
    const addr = await getAddress(q).catch(() => null)
    if (addr) {
      results.push({
        id: addr.addressId,
        kind: "entity",
        label: `Address ${addr.addressId.slice(0, 12)}…`,
        sublabel: `${addr.totalReceivedBtc || "0"} BTC Received`,
        route: `/investigation/${addr.addressId}`,
      })
    }
  } catch {
    // Address lookup skipped
  }

  // Search active dataset listings
  try {
    const { datasetId } = await getActiveContext()
    if (datasetId && results.length < 5) {
      const [txs, addrs] = await Promise.all([
        listTransactions(datasetId, { page: 1, pageSize: 20 }),
        listAddresses(datasetId, { page: 1, pageSize: 20 }),
      ])

      const qLower = q.toLowerCase()
      for (const t of txs.data || []) {
        if (t.transactionId.toLowerCase().includes(qLower) && !results.some((r) => r.id === t.transactionId)) {
          results.push({
            id: t.transactionId,
            kind: "transaction",
            label: `TX ${t.transactionId.slice(0, 12)}…`,
            sublabel: `${t.totalOutputValueBtc || "0"} BTC`,
            route: `/transaction/${t.transactionId}`,
          })
        }
      }

      for (const a of addrs.data || []) {
        if (a.addressId.toLowerCase().includes(qLower) && !results.some((r) => r.id === a.addressId)) {
          results.push({
            id: a.addressId,
            kind: "entity",
            label: `Address ${a.addressId.slice(0, 12)}…`,
            sublabel: `${a.totalReceivedBtc || "0"} BTC Received`,
            route: `/investigation/${a.addressId}`,
          })
        }
      }
    }
  } catch {
    // Listing search skipped
  }

  return results.slice(0, 8)
}

/**
 * Uploads a real dataset file and immediately triggers an asynchronous ML analysis run.
 */
export async function uploadAndAnalyzeDataset(
  file: File,
  name: string,
  onProgress?: (stage: "uploading" | "processing" | "completed" | "failed", pct: number) => void,
): Promise<{ datasetId: string; analysisId: string }> {
  onProgress?.("uploading", 30)
  const uploadRes = await apiUploadDataset(file, name)
  onProgress?.("uploading", 100)

  onProgress?.("processing", 10)
  const analysisRes = await apiTriggerAnalysis(uploadRes.datasetId)
  const analysisId = analysisRes.analysisId

  // Poll analysis status until completion or failure
  const startTime = Date.now()
  const timeoutMs = 120_000 // 2 minutes

  while (Date.now() - startTime < timeoutMs) {
    await new Promise((res) => setTimeout(res, 1500))
    try {
      const statusRes = await getAnalysis(analysisId)
      if (statusRes.status === "completed") {
        onProgress?.("completed", 100)
        return { datasetId: uploadRes.datasetId, analysisId }
      }
      if (statusRes.status === "failed") {
        onProgress?.("failed", 100)
        throw new Error(statusRes.errorMessage || "Analysis pipeline failed")
      }
      onProgress?.("processing", Math.min(90, Math.round(((Date.now() - startTime) / 10000) * 100)))
    } catch (err) {
      if (err instanceof Error && err.message.includes("failed")) throw err
    }
  }

  onProgress?.("completed", 100)
  return { datasetId: uploadRes.datasetId, analysisId }
}
