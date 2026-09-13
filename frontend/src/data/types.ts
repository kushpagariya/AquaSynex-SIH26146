/**
 * Domain contract for the BTC Investigator frontend.
 *
 * The UI never computes risk, anomalies, or graph structure — it only
 * visualizes what the backend / ML pipeline returns in these shapes.
 * When the real system is wired in, these types are the integration seam.
 */

export type Severity = "low" | "medium" | "high" | "critical"

export type AlertStatus = "new" | "reviewing" | "escalated" | "resolved" | "dismissed"

export type EntityType = "wallet" | "transaction" | "ip" | "network" | "exchange" | "mixer"

export type DatasetStage = "idle" | "uploading" | "processing" | "completed" | "failed"

/** A single contributing factor emitted by the ML model. */
export interface RiskFactor {
  id: string
  label: string
  /** 0-1 weight of this factor's contribution to the overall score. */
  weight: number
  description: string
}

export interface RiskProfile {
  /** 0-100, computed upstream. */
  score: number
  severity: Severity
  factors: RiskFactor[]
  /** Free-text model rationale, optional. */
  summary?: string
}

export interface NetworkInfo {
  ip: string
  port: number
  asn: string
  asnOrg: string
  country: string
  countryCode: string
  firstSeen: string
  lastSeen: string
}

export interface Entity {
  id: string
  type: EntityType
  label: string
  /** Canonical on-chain address / identifier where applicable. */
  address?: string
  risk: RiskProfile
  firstSeen: string
  lastSeen: string
  totalTransactions: number
  totalReceived: number
  totalSent: number
  balance: number
  tags: string[]
  network?: NetworkInfo
  connectedEntityIds: string[]
}

export interface Alert {
  id: string
  entityId: string
  entityLabel: string
  entityType: EntityType
  riskScore: number
  severity: Severity
  reason: string
  timestamp: string
  status: AlertStatus
}

export interface TxIO {
  entityId?: string
  address: string
  amount: number
}

export interface Transaction {
  txid: string
  timestamp: string
  amount: number
  fee: number
  confirmations: number
  block: number
  inputs: TxIO[]
  outputs: TxIO[]
  network: NetworkInfo
  relatedEntityIds: string[]
  riskScore?: number
  severity?: Severity
  behaviorType?: string
  clusterId?: string
  status?: string
}

export type TimelineKind =
  | "transaction"
  | "counterparty"
  | "burst"
  | "network"
  | "high-risk"
  | "flag"

export interface TimelineEvent {
  id: string
  timestamp: string
  kind: TimelineKind
  title: string
  detail: string
  severity?: Severity
  txid?: string
}

export type EvidenceCategory =
  | "behavioral"
  | "transaction"
  | "network"
  | "connections"
  | "model"

export interface EvidenceItem {
  id: string
  category: EvidenceCategory
  title: string
  detail: string
  severity: Severity
  timestamp?: string
}

/** Graph node/edge shapes consumed by the Cytoscape viewer. */
export interface GraphNode {
  id: string
  label: string
  type: EntityType
  severity?: Severity
  isFocus?: boolean
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label?: string
  amount?: number
  suspicious?: boolean
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

/** Everything the Investigation page needs for a single entity. */
export interface Investigation {
  entity: Entity
  transactions: Transaction[]
  connectedEntities: Entity[]
  timeline: TimelineEvent[]
  evidence: EvidenceItem[]
  graph: GraphData
}

export interface AnomalyBucket {
  label: string
  transactions: number
  anomalies: number
}

export interface DashboardStats {
  totalTransactions: number
  totalEntities: number
  suspiciousEntities: number
  highRiskEntities: number
  activeAlerts: number
  anomaliesDetected: number
  lastProcessed?: string
  processingStatus?: {
    ingestion: boolean
    entityResolution: boolean
    riskScoring: boolean
    graphBuild: boolean
  }
  deltas: {
    transactions: number
    entities: number
    alerts: number
    highRisk: number
  }
  anomalySeries: AnomalyBucket[]
}

export interface DatasetInfo {
  id: string
  name: string
  sizeBytes: number
  format: string
  uploadedAt: string
  stage: DatasetStage
  progress: number
  stats?: {
    transactions: number
    entities: number
    addresses: number
    blocks: number
    dateRange: { from: string; to: string }
    flagged: number
    span?: string
  }
  error?: string
}

/** Canonical Inferred Behavioral Cluster emitted by pipeline */
export interface InferredCluster {
  clusterId: string
  clusterSize: number
  transactionCount: number
  totalReceived: number
  totalSent: number
  balance: number
  averageRisk: number
  highestRisk: number
  severity: Severity
  dominantBehavior: string
  status: "Active" | "Elevated Risk" | "Monitored"
  associatedAddresses: string[]
  firstSeen: string
  lastSeen: string
  leadAddress: string
}

export interface NetworkDistributionItem {
  key: string
  label: string
  count: number
  percentage: number
  volumeBtc: number
  riskCount: number
}

export interface NetworkIntelligenceData {
  countries: NetworkDistributionItem[]
  asns: NetworkDistributionItem[]
  ports: {
    standardPortCount: number
    nonStandardPortCount: number
    srcPorts: { port: number; count: number }[]
    dstPorts: { port: number; count: number }[]
  }
  timeline: { time: string; count: number; suspicious: number }[]
  suspiciousEvents: {
    txid: string
    ip: string
    port: number
    asn: string
    asnOrg: string
    country: string
    riskScore: number
    severity: Severity
    timestamp: string
    behaviorType?: string
  }[]
  topIps: { ip: string; country: string; asn: string; txCount: number; volumeBtc: number; maxRisk: number }[]
  topAsns: { asn: string; asnOrg: string; country: string; txCount: number; volumeBtc: number }[]
}

export const BEHAVIOR_TYPOLOGIES = [
  "normal",
  "benign_high_volume",
  "transaction_burst",
  "rapid_multihop",
  "peeling_chain",
  "coordinated_activity",
  "high_fan_in",
  "high_fan_out",
  "temporal_anomaly",
  "mixing_like",
  "amount_anomaly",
] as const

export type BehaviorTypology = (typeof BEHAVIOR_TYPOLOGIES)[number]

export interface BehaviorAnalyticsItem {
  key: BehaviorTypology
  name: string
  description: string
  count: number
  percentage: number
  averageRisk: number
  severityBreakdown: Record<Severity, number>
  topTransactions: { txid: string; amount: number; timestamp: string; riskScore: number; severity: Severity }[]
  topEntities: { id: string; label: string; address?: string; riskScore: number; severity: Severity }[]
}

export interface ModelOperatingPoint {
  threshold: number
  valRecall: number
  valPrecision: number
  valF1: number
  testRecall: number
  testPrecision: number
  testF1: number
}

export interface FeatureGroupInfo {
  name: string
  count: number
  description: string
  features: string[]
  subtypes?: string
}

export interface ModelInsightsData {
  binaryModel: {
    algorithm: string
    version: string
    releaseTag: string
    operatingPoints: {
      defaultPoint: ModelOperatingPoint
      f1Optimal: ModelOperatingPoint
      highPrecisionR95: ModelOperatingPoint
    }
    generalization: {
      valRocAuc: number
      testRocAuc: number
      valPrAuc: number
      testPrAuc: number
    }
  }
  multiclassModel: {
    algorithm: string
    version: string
    classesCount: number
    classes: string[]
    accuracy: number
    macroF1: number
  }
  featureGroups: FeatureGroupInfo[]
  topShapFeatures: {
    rank: number
    featureName: string
    displayLabel: string
    group: string
    unit?: string
    importance: number
    direction: "increases_risk" | "decreases_risk" | "neutral"
  }[]
  scientificDisclaimer: string
}

export interface DatasetProfile {
  totalTransactions: number
  totalAddresses: number
  totalEntities: number
  timeRange: { from: string; to: string; span: string }
  countryCount: number
  asnCount: number
  suspiciousPercentage: number
  missingValues: number
  duplicateIds: number
  behaviorDistribution: { behavior: string; count: number; percentage: number }[]
  graphCoverage: { nodeCount: number; edgeCount: number; isCovered: boolean }
  scoringStatus: { scoredCount: number; totalCount: number; status: string }
}

