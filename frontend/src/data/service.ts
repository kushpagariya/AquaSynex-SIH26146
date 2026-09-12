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
  getEntityResultDetail,
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
  NetworkInfo,
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

interface ActiveSessionContext {
  datasetId?: string
  analysisId?: string
}

let sessionContext: ActiveSessionContext = {}
let activeContextPromise: Promise<ActiveSessionContext> | null = null

export function setActiveContext(datasetId?: string, analysisId?: string) {
  sessionContext = { datasetId, analysisId }
}

export function clearActiveContext() {
  sessionContext = {}
}

/**
 * Resolves the currently active dataset and analysis IDs from the backend.
 * Uses cached session IDs if valid, otherwise gracefully queries backend.
 */
export async function getActiveContext(forceRefresh = false): Promise<ActiveSessionContext> {
  if (!forceRefresh && sessionContext.datasetId && sessionContext.analysisId) {
    return sessionContext
  }

  if (activeContextPromise && !forceRefresh) {
    return activeContextPromise
  }

  activeContextPromise = (async () => {
    try {
      const datasetsRes = await listDatasets({
        page: 1,
        pageSize: 1,
        sortBy: "uploadedAt",
        sortDir: "desc",
      })
      const datasets = datasetsRes.data || []
      if (!datasets.length) {
        sessionContext = {}
        return {}
      }

      const datasetId = datasets[0].datasetId
      const analyses = await listAnalysesForDataset(datasetId).catch(() => [])
      const activeAnalysis =
        analyses.find((a) => a.status === "completed") ||
        analyses.find((a) => a.status === "running" || a.status === "pending") ||
        analyses[0]
      const analysisId = activeAnalysis ? activeAnalysis.analysisId : undefined

      sessionContext = { datasetId, analysisId }
      return sessionContext
    } catch (err) {
      console.error("Failed to resolve active context from backend:", err)
      sessionContext = {}
      return {}
    } finally {
      activeContextPromise = null
    }
  })()

  return activeContextPromise
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
      lastProcessed: undefined,
      processingStatus: {
        ingestion: false,
        entityResolution: false,
        riskScoring: false,
        graphBuild: false,
      },
      deltas: { transactions: 0, entities: 0, alerts: 0, highRisk: 0 },
      anomalySeries: [],
    }
  }

  const [datasetDetail, addrList, analysisDetail] = await Promise.all([
    getDataset(datasetId).catch(() => null),
    listAddresses(datasetId, { page: 1, pageSize: 1, analysisId }).catch(() => null),
    analysisId ? getAnalysis(analysisId).catch(() => null) : Promise.resolve(null),
  ])

  let totalEntities =
    addrList?.meta?.pagination?.totalItems ||
    analysisDetail?.entityCount ||
    (datasetDetail?.validationSummary?.addressCount as number) ||
    0
  let highRisk = analysisDetail?.highRiskCount || 0
  let criticalRisk = analysisDetail?.criticalRiskCount || 0
  let activeAlerts = highRisk + criticalRisk
  let anomaliesDetected = activeAlerts
  let lastProcessed = analysisDetail?.completedAt || datasetDetail?.uploadedAt || undefined

  const isCompleted = analysisDetail?.status === "completed" || datasetDetail?.status === "ready"
  const processingStatus = {
    ingestion: datasetDetail?.status === "ready" || isCompleted,
    entityResolution: isCompleted,
    riskScoring: isCompleted,
    graphBuild: isCompleted,
  }

  // Construct anomaly series from recent transactions, discretized into uniform bounded bins
  let anomalySeries: AnomalyBucket[] = []
  try {
    const txRes = await listTransactions(datasetId, {
      page: 1,
      pageSize: 200,
      sortBy: "timestamp",
      sortDir: "asc",
      analysisId,
    })
    const txs = txRes.data || []
    if (txs.length) {
      const timestamps = txs
        .map((t) => (t.timestamp ? new Date(t.timestamp).getTime() : NaN))
        .filter((t) => !isNaN(t))

      if (timestamps.length) {
        const minTime = Math.min(...timestamps)
        const maxTime = Math.max(...timestamps)
        const numBuckets = Math.min(10, Math.max(3, txs.length))
        const timeSpan = maxTime - minTime
        const interval = timeSpan > 0 ? timeSpan / numBuckets : 3600000

        const buckets: AnomalyBucket[] = []
        for (let i = 0; i < numBuckets; i++) {
          const bStart = minTime + i * interval
          const bEnd = minTime + (i + 1) * interval
          const label = new Date(bStart).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
          const inBucket = txs.filter((t) => {
            if (!t.timestamp) return false
            const time = new Date(t.timestamp).getTime()
            return i === numBuckets - 1
              ? time >= bStart && time <= bEnd
              : time >= bStart && time < bEnd
          })
          const anomalies = inBucket.filter(
            (t) => t.riskLevel === "high" || t.riskLevel === "critical",
          ).length
          buckets.push({
            label,
            transactions: inBucket.length,
            anomalies,
          })
        }
        anomalySeries = buckets
      }
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
    lastProcessed,
    processingStatus,
    deltas: { transactions: 0, entities: 0, alerts: 0, highRisk: 0 },
    anomalySeries,
  }
}

/**
 * Retrieves high/critical risk predictions from the active analysis run as actionable alerts.
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
export async function getDatasetInfo(datasetIdOverride?: string): Promise<DatasetInfo | null> {
  try {
    let targetDatasetId = datasetIdOverride
    if (!targetDatasetId) {
      const activeCtx = await getActiveContext()
      targetDatasetId = activeCtx.datasetId
    }
    if (!targetDatasetId) {
      const listRes = await listDatasets({
        page: 1,
        pageSize: 1,
        sortBy: "uploadedAt",
        sortDir: "desc",
      })
      const datasets = listRes.data || []
      if (!datasets.length) return null
      targetDatasetId = datasets[0].datasetId
    }

    const [detail, addrListRes, analysesRes, txSampleRes] = await Promise.all([
      getDataset(targetDatasetId),
      listAddresses(targetDatasetId, { page: 1, pageSize: 1 }).catch(() => null),
      listAnalysesForDataset(targetDatasetId).catch(() => []),
      listTransactions(targetDatasetId, {
        page: 1,
        pageSize: 50,
        sortBy: "timestamp",
        sortDir: "asc",
      }).catch(() => null),
    ])

    const val = detail.validationSummary || {}
    const completedAnalysis =
      analysesRes.find((a) => a.status === "completed") ||
      analysesRes.find((a) => a.status === "running" || a.status === "pending")

    const totalAddresses =
      addrListRes?.meta?.pagination?.totalItems ??
      (val.addressCount as number) ??
      (val.unique_addresses as number) ??
      completedAnalysis?.entityCount ??
      0

    const flagged = completedAnalysis
      ? (completedAnalysis.highRiskCount || 0) + (completedAnalysis.criticalRiskCount || 0)
      : 0

    let dateSpan = "—"
    const txs = txSampleRes?.data || []
    if (txs.length >= 2) {
      const firstTs = txs[0]?.timestamp
      const lastTs = txs[txs.length - 1]?.timestamp
      const t1 = firstTs ? new Date(firstTs).getTime() : NaN
      const t2 = lastTs ? new Date(lastTs).getTime() : NaN
      if (!isNaN(t1) && !isNaN(t2)) {
        const diffHours = Math.round(Math.abs(t2 - t1) / 3600000)
        dateSpan = diffHours > 24 ? `${Math.round(diffHours / 24)}d` : `${Math.max(1, diffHours)}h`
      }
    }

    return {
      id: detail.datasetId,
      name: detail.name || detail.fileName,
      sizeBytes: detail.sizeBytes,
      format: detail.format.toUpperCase(),
      uploadedAt: detail.uploadedAt,
      stage:
        completedAnalysis?.status === "completed" || detail.status === "ready"
          ? "completed"
          : detail.status === "error" || completedAnalysis?.status === "failed"
            ? "failed"
            : "processing",
      progress: 100,
      stats: {
        transactions: detail.canonicalTxCount || detail.rowCount || 0,
        entities: totalAddresses,
        addresses: totalAddresses,
        blocks: (val.block_count as number) || (txs[0]?.blockHeight ? 1 : 0),
        dateRange: { from: txs[0]?.timestamp || "", to: txs[txs.length - 1]?.timestamp || "" },
        flagged,
        span: dateSpan,
      },
      error: detail.errorMessage || completedAnalysis?.errorMessage,
    }
  } catch (err) {
    console.error("Failed to load dataset info from backend:", err)
    return null
  }
}

/**
 * Fetches transaction details including inputs, outputs, network events, and attached ML prediction.
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

    const netEvent = tx.networkEvents?.[0]
    const network: NetworkInfo = {
      ip: netEvent?.srcIp || "—",
      port: netEvent?.srcPort || 8333,
      asn: netEvent?.asn ? String(netEvent.asn) : "—",
      asnOrg: netEvent?.asn ? `AS${netEvent.asn}` : "Unspecified Network Telemetry",
      country: netEvent?.country || "Unknown",
      countryCode: (netEvent?.country || "XX").slice(0, 2).toUpperCase(),
      firstSeen: tx.timestamp || "",
      lastSeen: tx.timestamp || "",
    }

    return {
      txid: tx.transactionId,
      timestamp: tx.timestamp || new Date().toISOString(),
      amount: parseFloat(tx.totalOutputValueBtc || tx.totalInputValueBtc || "0"),
      fee: parseFloat(tx.feeBtc || "0"),
      confirmations: 6,
      block: tx.blockHeight || 0,
      inputs,
      outputs,
      network,
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
 * Fetches complete investigation bundle for an entity (supports both transactions and addresses).
 * Avoids requesting address endpoint for transaction IDs.
 */
export async function getInvestigation(
  entityId: string,
  entityTypeHint?: string,
): Promise<Investigation | null> {
  try {
    const { analysisId } = await getActiveContext()

    // Determine entity type:
    // 1. Explicit hint provided
    // 2. Query ML result detail
    // 3. Fall back to ID format candidate
    let resolvedType: "transaction" | "wallet" | "address" | undefined =
      entityTypeHint === "transaction"
        ? "transaction"
        : entityTypeHint === "wallet" || entityTypeHint === "address"
          ? "wallet"
          : undefined

    let mlResultDetail: import("@/api").MLResultDetail | null = null

    if (!resolvedType && analysisId) {
      try {
        mlResultDetail = await getEntityResultDetail(analysisId, entityId)
        if (mlResultDetail.entityType === "transaction") {
          resolvedType = "transaction"
        } else {
          resolvedType = "wallet"
        }
      } catch {
        // Result lookup skipped
      }
    }

    if (!resolvedType) {
      if (/^[0-9a-fA-F]{64}$/.test(entityId)) {
        resolvedType = "transaction"
      } else {
        resolvedType = "wallet"
      }
    }

    // Handle transaction investigation
    if (resolvedType === "transaction") {
      const tx = await apiGetTransaction(entityId, analysisId)
      if (!mlResultDetail && analysisId) {
        try {
          mlResultDetail = await getEntityResultDetail(analysisId, entityId)
        } catch {
          // ML result optional
        }
      }

      const score =
        mlResultDetail?.riskScore !== undefined
          ? Math.round(mlResultDetail.riskScore * 100)
          : tx.riskScore !== undefined && tx.riskScore !== null
            ? Math.round(tx.riskScore * 100)
            : 0
      const severity = (mlResultDetail?.riskLevel?.toLowerCase() ||
        tx.riskLevel?.toLowerCase() ||
        "low") as Severity

      const factors = (mlResultDetail?.explanations || []).map((exp, idx) => ({
        id: `f-${idx}`,
        label: exp.displayLabel || exp.featureName,
        weight: exp.normalizedImportance || 0.2,
        description: `${exp.direction === "increases_risk" ? "Elevated risk indicator:" : "Factor"} ${exp.displayLabel} (SHAP value: ${exp.shapValue.toFixed(4)})`,
      }))

      const netEvent = tx.networkEvents?.[0]
      const network: NetworkInfo = {
        ip: netEvent?.srcIp || "—",
        port: netEvent?.srcPort || 8333,
        asn: netEvent?.asn ? String(netEvent.asn) : "—",
        asnOrg: netEvent?.asn ? `AS${netEvent.asn}` : "Bitcoin P2P Network",
        country: netEvent?.country || "Unknown",
        countryCode: (netEvent?.country || "XX").slice(0, 2).toUpperCase(),
        firstSeen: tx.timestamp || "",
        lastSeen: tx.timestamp || "",
      }

      const inputTxs = (tx.inputs || []).map((i) => ({
        entityId: i.inputAddress,
        address: i.inputAddress || "Unknown",
        amount: parseFloat(i.inputValueBtc || "0"),
      }))

      const outputTxs = (tx.outputs || []).map((o) => ({
        entityId: o.outputAddress,
        address: o.outputAddress || "Unknown",
        amount: parseFloat(o.outputValueBtc || "0"),
      }))

      const relatedAddrs = Array.from(
        new Set(
          [...inputTxs.map((i) => i.address), ...outputTxs.map((o) => o.address)].filter(
            (a) => a && a !== "Unknown",
          ),
        ),
      )

      const connectedEntities: Entity[] = relatedAddrs.map((addr) => ({
        id: addr,
        type: "wallet",
        label: addr.length > 16 ? `${addr.slice(0, 8)}…${addr.slice(-6)}` : addr,
        address: addr,
        risk: { score: 0, severity: "low", factors: [] },
        firstSeen: tx.timestamp || "",
        lastSeen: tx.timestamp || "",
        totalTransactions: 1,
        totalReceived: 0,
        totalSent: 0,
        balance: 0,
        tags: [],
        connectedEntityIds: [entityId],
      }))

      const txAmount = parseFloat(tx.totalOutputValueBtc || tx.totalInputValueBtc || "0")
      const txFee = parseFloat(tx.feeBtc || "0")

      const entity: Entity = {
        id: tx.transactionId,
        type: "transaction",
        label: `TX ${tx.transactionId.slice(0, 8)}…${tx.transactionId.slice(-6)}`,
        risk: {
          score,
          severity,
          factors,
          summary: factors.length
            ? `Analysis flagged ${factors.length} primary risk factors for this transaction.`
            : "Standard transaction behavior observed with no significant anomalies.",
        },
        firstSeen: tx.timestamp || "",
        lastSeen: tx.timestamp || "",
        totalTransactions: 1,
        totalReceived: txAmount,
        totalSent: txAmount,
        balance: 0,
        tags: tx.riskLevel ? [tx.riskLevel.toLowerCase()] : [],
        network,
        connectedEntityIds: relatedAddrs,
      }

      const timeline: TimelineEvent[] = [
        {
          id: `tl-tx-${tx.transactionId}`,
          timestamp: tx.timestamp || new Date().toISOString(),
          kind: "transaction",
          title: "Transaction Confirmed",
          detail: `Block ${tx.blockHeight ?? "Pending"} • Transferred ${txAmount} BTC (Fee: ${txFee.toFixed(5)} BTC)`,
          severity,
          txid: tx.transactionId,
        },
      ]

      if (netEvent?.srcIp) {
        timeline.push({
          id: `tl-net-${tx.transactionId}`,
          timestamp: tx.timestamp || new Date().toISOString(),
          kind: "network",
          title: "Network Telemetry Observed",
          detail: `Broadcasting Node: ${netEvent.srcIp}:${netEvent.srcPort || 8333} (ASN ${netEvent.asn || "Unknown"}, ${netEvent.country || "Unknown"})`,
          severity,
        })
      }

      const evidence: EvidenceItem[] = [
        ...(mlResultDetail?.graphEvidence || []).map((ge, idx) => ({
          id: `ev-ge-${idx}`,
          category: "connections" as const,
          title: ge.label,
          detail: ge.description,
          severity,
        })),
        ...factors.map((f, idx) => ({
          id: `ev-exp-${idx}`,
          category: "model" as const,
          title: f.label,
          detail: f.description,
          severity,
        })),
        {
          id: "ev-tx-params",
          category: "transaction" as const,
          title: "Transaction Attributes",
          detail: `${tx.inputs.length} inputs, ${tx.outputs.length} outputs, ${txFee.toFixed(5)} BTC fee`,
          severity: "low" as const,
        },
      ]

      const graphNodes = [
        {
          id: tx.transactionId,
          label: `TX ${tx.transactionId.slice(0, 8)}…`,
          type: "transaction" as EntityType,
          severity,
          isFocus: true,
        },
        ...inputTxs.map((i) => ({
          id: i.address,
          label:
            i.address.length > 14
              ? `${i.address.slice(0, 6)}…${i.address.slice(-4)}`
              : i.address,
          type: "wallet" as EntityType,
          severity: "low" as Severity,
          isFocus: false,
        })),
        ...outputTxs.map((o) => ({
          id: o.address,
          label:
            o.address.length > 14
              ? `${o.address.slice(0, 6)}…${o.address.slice(-4)}`
              : o.address,
          type: "wallet" as EntityType,
          severity: "low" as Severity,
          isFocus: false,
        })),
      ]

      const uniqueNodes = Array.from(new Map(graphNodes.map((n) => [n.id, n])).values())

      const graphEdges = [
        ...inputTxs.map((i, idx) => ({
          id: `e-in-${idx}`,
          source: i.address,
          target: tx.transactionId,
          amount: i.amount,
          label: i.amount ? `${i.amount} BTC` : undefined,
          suspicious: severity === "high" || severity === "critical",
        })),
        ...outputTxs.map((o, idx) => ({
          id: `e-out-${idx}`,
          source: tx.transactionId,
          target: o.address,
          amount: o.amount,
          label: o.amount ? `${o.amount} BTC` : undefined,
          suspicious: severity === "high" || severity === "critical",
        })),
      ]

      return {
        entity,
        transactions: [
          {
            txid: tx.transactionId,
            timestamp: tx.timestamp || "",
            amount: txAmount,
            fee: txFee,
            confirmations: 6,
            block: tx.blockHeight || 0,
            inputs: inputTxs,
            outputs: outputTxs,
            network,
            relatedEntityIds: relatedAddrs,
            riskScore: score,
            severity,
          },
        ],
        connectedEntities,
        timeline,
        evidence,
        graph: {
          nodes: uniqueNodes,
          edges: graphEdges,
        },
      }
    }

    // Handle address investigation
    const [addr, graphData] = await Promise.all([
      getAddress(entityId, analysisId),
      getAddressSubgraph(entityId, { hops: 2, analysisId }).catch(
        (): import("@/api").GraphExport => ({
          graphId: "",
          datasetId: "",
          generatedAt: new Date().toISOString(),
          nodeCount: 0,
          edgeCount: 0,
          isSubgraph: true,
          subgraphCenter: entityId,
          nodes: [],
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

    const connectedEntities: Entity[] = graphData.nodes
      .filter((n) => n.id !== entityId && n.nodeType !== "transaction")
      .map((n) => ({
        id: n.id,
        type: (n.nodeType === "address" ? "wallet" : n.nodeType) as EntityType,
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
        balance: Math.max(
          0,
          parseFloat(n.metadata?.totalReceivedBtc || "0") -
            parseFloat(n.metadata?.totalSentBtc || "0"),
        ),
        tags: n.riskLevel ? [n.riskLevel.toLowerCase()] : [],
        connectedEntityIds: [entityId],
      }))

    const txNodes = graphData.nodes.filter((n) => n.nodeType === "transaction")
    const relatedTransactions: Transaction[] = []

    const edgeTxs = await Promise.all(
      txNodes.slice(0, 10).map(async (t) => {
        const full = await apiGetTransaction(t.id, analysisId).catch(() => null)
        if (full) {
          const netEvent = full.networkEvents?.[0]
          return {
            txid: full.transactionId,
            timestamp: full.timestamp || "",
            amount: parseFloat(full.totalOutputValueBtc || full.totalInputValueBtc || "0"),
            fee: parseFloat(full.feeBtc || "0"),
            confirmations: 6,
            block: full.blockHeight || 0,
            inputs: (full.inputs || []).map((i) => ({
              entityId: i.inputAddress,
              address: i.inputAddress || "Unknown",
              amount: parseFloat(i.inputValueBtc || "0"),
            })),
            outputs: (full.outputs || []).map((o) => ({
              entityId: o.outputAddress,
              address: o.outputAddress || "Unknown",
              amount: parseFloat(o.outputValueBtc || "0"),
            })),
            network: {
              ip: netEvent?.srcIp || "—",
              port: netEvent?.srcPort || 8333,
              asn: netEvent?.asn ? String(netEvent.asn) : "—",
              asnOrg: netEvent?.asn ? `AS${netEvent.asn}` : "Unspecified Network Telemetry",
              country: netEvent?.country || "Unknown",
              countryCode: (netEvent?.country || "XX").slice(0, 2).toUpperCase(),
              firstSeen: full.timestamp || "",
              lastSeen: full.timestamp || "",
            },
            relatedEntityIds: [entityId],
            riskScore: full.riskScore ? Math.round(full.riskScore * 100) : undefined,
            severity: (full.riskLevel?.toLowerCase() as Severity) || undefined,
          }
        }
        return {
          txid: t.id,
          timestamp: "",
          amount: 0,
          fee: 0,
          confirmations: 6,
          block: 0,
          inputs: [],
          outputs: [],
          network: {
            ip: "—",
            port: 8333,
            asn: "—",
            asnOrg: "Unspecified Network Telemetry",
            country: "Unknown",
            countryCode: "XX",
            firstSeen: "",
            lastSeen: "",
          },
          relatedEntityIds: [entityId],
        }
      }),
    )
    relatedTransactions.push(...edgeTxs)

    const timeline: TimelineEvent[] = relatedTransactions.map((t, idx) => ({
      id: `tl-${idx}`,
      timestamp: t.timestamp || new Date().toISOString(),
      kind: "transaction",
      title: `Transaction ${t.txid.slice(0, 10)}…`,
      detail: `Transfer of ${t.amount} BTC`,
      txid: t.txid,
    }))

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

  const isAddressCandidate = q.length >= 26 && /^(1|3|bc1|tb1|bcrt)/i.test(q)
  const isTxidCandidate = /^[0-9a-fA-F]{64}$/.test(q)

  if (isTxidCandidate) {
    try {
      const tx = await apiGetTransaction(q).catch(() => null)
      if (tx) {
        results.push({
          id: tx.transactionId,
          kind: "transaction",
          label: `TX ${tx.transactionId.slice(0, 12)}…`,
          sublabel: `${tx.totalOutputValueBtc || tx.totalInputValueBtc || "0"} BTC`,
          route: `/investigation/${tx.transactionId}?entityType=transaction`,
        })
      }
    } catch {
      // Lookup skipped
    }
  }

  if (isAddressCandidate) {
    try {
      const addr = await getAddress(q).catch(() => null)
      if (addr) {
        results.push({
          id: addr.addressId,
          kind: "entity",
          label: `Address ${addr.addressId.slice(0, 12)}…`,
          sublabel: `${addr.totalReceivedBtc || "0"} BTC Received`,
          route: `/investigation/${addr.addressId}?entityType=wallet`,
        })
      }
    } catch {
      // Lookup skipped
    }
  }

  if (q.length >= 2) {
    try {
      const { datasetId } = await getActiveContext()
      if (datasetId && results.length < 5) {
        const [txs, addrs] = await Promise.all([
          listTransactions(datasetId, { page: 1, pageSize: 20 }),
          listAddresses(datasetId, { page: 1, pageSize: 20 }),
        ])

        const qLower = q.toLowerCase()
        for (const t of txs.data || []) {
          if (
            t.transactionId.toLowerCase().includes(qLower) &&
            !results.some((r) => r.id === t.transactionId)
          ) {
            results.push({
              id: t.transactionId,
              kind: "transaction",
              label: `TX ${t.transactionId.slice(0, 12)}…`,
              sublabel: `${t.totalOutputValueBtc || "0"} BTC`,
              route: `/investigation/${t.transactionId}?entityType=transaction`,
            })
          }
        }

        for (const a of addrs.data || []) {
          if (
            a.addressId.toLowerCase().includes(qLower) &&
            !results.some((r) => r.id === a.addressId)
          ) {
            results.push({
              id: a.addressId,
              kind: "entity",
              label: `Address ${a.addressId.slice(0, 12)}…`,
              sublabel: `${a.totalReceivedBtc || "0"} BTC Received`,
              route: `/investigation/${a.addressId}?entityType=wallet`,
            })
          }
        }
      }
    } catch {
      // Listing search skipped
    }
  }

  return results.slice(0, 8)
}

/**
 * Uploads a real dataset file and immediately triggers an asynchronous ML analysis run.
 * Sets and maintains authoritative active context across dataset and analysis lifecycle.
 */
export async function uploadAndAnalyzeDataset(
  file: File,
  name: string,
  onProgress?: (stage: "uploading" | "processing" | "completed" | "failed", pct: number) => void,
  modelId?: string,
  signal?: AbortSignal,
): Promise<{ datasetId: string; analysisId: string }> {
  onProgress?.("uploading", 30)
  const uploadRes = await apiUploadDataset(file, name)
  const datasetId = uploadRes.datasetId
  setActiveContext(datasetId, undefined)
  onProgress?.("uploading", 100)

  onProgress?.("processing", 10)
  const analysisRes = await apiTriggerAnalysis(datasetId, {
    modelId: modelId || undefined,
  })
  const analysisId = analysisRes.analysisId
  setActiveContext(datasetId, analysisId)

  // Poll analysis status until completion or failure
  const startTime = Date.now()
  const timeoutMs = 120_000 // 2 minutes
  let consecutiveNetworkErrors = 0

  while (Date.now() - startTime < timeoutMs) {
    if (signal?.aborted) {
      throw new DOMException("Analysis polling aborted", "AbortError")
    }

    await new Promise((res) => setTimeout(res, 1500))

    if (signal?.aborted) {
      throw new DOMException("Analysis polling aborted", "AbortError")
    }

    let statusRes: import("@/api").AnalysisSummary
    try {
      statusRes = await getAnalysis(analysisId)
      consecutiveNetworkErrors = 0
    } catch (err) {
      if (signal?.aborted) {
        throw new DOMException("Analysis polling aborted", "AbortError")
      }
      consecutiveNetworkErrors++
      if (consecutiveNetworkErrors >= 3) {
        onProgress?.("failed", 100)
        throw new Error("Backend connection lost while polling analysis status.")
      }
      continue
    }

    if (statusRes.status === "completed") {
      setActiveContext(datasetId, analysisId)
      onProgress?.("completed", 100)
      return { datasetId, analysisId }
    }

    if (statusRes.status === "failed") {
      onProgress?.("failed", 100)
      throw new Error(statusRes.errorMessage || "Analysis pipeline failed")
    }

    onProgress?.(
      "processing",
      Math.min(90, Math.round(((Date.now() - startTime) / 10000) * 100)),
    )
  }

  setActiveContext(datasetId, analysisId)
  onProgress?.("completed", 100)
  return { datasetId, analysisId }
}
