/**
 * Backend DTO types strictly aligned with FastAPI backend schemas.
 * Authoritative source: docs/backend/request-response-schemas.md & backend/schemas/*.py
 */

export interface PaginationMeta {
  page: number
  pageSize: number
  totalItems: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean
}

export interface ApiMeta {
  timestamp: string
  requestId: string
  pagination?: PaginationMeta
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiError
  meta: ApiMeta
}

export interface DatasetSummary {
  datasetId: string
  name: string
  fileName: string
  format: string
  sizeBytes: number
  rowCount?: number
  status: string
  uploadedAt: string
  availableFields: string[]
}

export interface DatasetDetail extends DatasetSummary {
  canonicalTxCount?: number
  validationSummary?: Record<string, unknown>
  errorMessage?: string
}

export interface DatasetUploadResponse {
  datasetId: string
  name: string
  status: string
  uploadedAt: string
}

export interface AnalysisSummary {
  analysisId: string
  datasetId: string
  status: string
  startedAt?: string
  completedAt?: string
  modelId?: string
  modelVersion?: string
  entityCount?: number
  highRiskCount?: number
  criticalRiskCount?: number
  errorMessage?: string
}

export interface AnalysisTriggerResponse {
  analysisId: string
  datasetId: string
  status: string
  startedAt: string
}

export interface TransactionSummary {
  transactionId: string
  blockHeight?: number
  timestamp?: string
  inputCount?: number
  outputCount?: number
  totalInputValueBtc?: string
  totalOutputValueBtc?: string
  feeBtc?: string
  riskScore?: number
  riskLevel?: string
}

export interface TransactionInputDetail {
  inputIndex: number
  inputAddress?: string
  inputValueBtc?: string
}

export interface TransactionOutputDetail {
  outputIndex: number
  outputAddress?: string
  outputValueBtc?: string
  scriptType?: string
}

export interface NetworkEventSchema {
  srcIp?: string | null
  srcPort?: number | null
  dstIp?: string | null
  dstPort?: number | null
  country?: string | null
  asn?: number | null
}

export interface TransactionDetail extends TransactionSummary {
  blockHash?: string
  transactionSizeBytes?: number
  label?: string
  inputs: TransactionInputDetail[]
  outputs: TransactionOutputDetail[]
  networkEvents?: NetworkEventSchema[]
  mlResult?: MLResultSummary
}

export interface AddressSummary {
  addressId: string
  transactionCount?: number
  totalReceivedBtc?: string
  totalSentBtc?: string
  firstSeen?: string
  lastSeen?: string
  riskScore?: number
  riskLevel?: string
}

export interface AddressDetail extends AddressSummary {
  addressType?: string
  activeDays?: number
  mlResult?: MLResultDetail
}

export interface NodeMetadata {
  transactionCount?: number
  totalReceivedBtc?: string
  totalSentBtc?: string
  firstSeen?: string
  lastSeen?: string
  activeDays?: number
  amountBtc?: string
  feeBtc?: string
  inputCount?: number
  outputCount?: number
  timestamp?: string
  blockHeight?: number
  feeRate?: number
  behavior?: string
  riskScore?: number
  riskLevel?: string
  evidence?: {
    graph?: Record<string, any>
    temporal?: Record<string, any>
    network?: Record<string, any>
    ml?: Record<string, any>
  }
  alerts?: Record<string, any>[]
  [key: string]: any
}

export interface GraphNodeDto {
  id: string
  label: string
  nodeType: string
  riskScore?: number
  riskLevel?: string
  behaviorType?: string
  metadata?: NodeMetadata
  alerts?: Record<string, any>[]
}

export interface GraphEdgeTransactionDto {
  transactionId: string
  valueSatoshi: number
  valueBtc: string
  timestamp?: string
}

export interface GraphEdgeDto {
  id: string
  source: string
  target: string
  edgeType: string
  transactions: GraphEdgeTransactionDto[]
  totalValueBtc: string
  totalValueSatoshi: number
  transactionCount: number
}

export interface GraphExport {
  graphId: string
  analysisId?: string
  datasetId: string
  generatedAt: string
  nodeCount: number
  edgeCount: number
  isSubgraph: boolean
  subgraphCenter?: string
  nodes: GraphNodeDto[]
  edges: GraphEdgeDto[]
}

export interface SelectedEntityInfo {
  entityId: string
  entityType: string
  label?: string
  exists: boolean
  riskScore?: number
  riskLevel?: string
  behaviorType?: string
  metadata?: Record<string, unknown>
  alerts?: Record<string, unknown>[]
}

export interface GraphSummary {
  nodeCount: number
  edgeCount: number
  depth: number
  highRiskOnly: boolean
  addressCount: number
  transactionCount: number
  clusterCount: number
}

export interface GraphNeighborhoodResponse extends GraphExport {
  selectedEntity?: SelectedEntityInfo
  summary?: GraphSummary
}

export interface FeatureExplanationSchema {
  featureName: string
  displayLabel: string
  shapValue: number
  direction: "increases_risk" | "decreases_risk" | "neutral"
  importanceRank: number
  normalizedImportance: number
  featureValue?: number | string | null
  featureUnit?: string | null
}

export interface FeatureValueSchema {
  featureName: string
  rawValue?: number | string | null
  normalizedValue?: number | null
  isImputed: boolean
  imputationMethod?: string | null
}

export interface GraphEvidenceSchema {
  evidenceType: string
  label: string
  featureName: string
  value: number
  description: string
}

export interface MLResultSummary {
  entityId: string
  entityType: string
  anomalyScore: number
  riskScore: number
  riskLevel: string
  predictionLabel?: string
  modelId: string
  modelVersion: string
  predictedAt: string
}

export interface MLResultDetail extends MLResultSummary {
  confidence?: number
  explanations: FeatureExplanationSchema[]
  features: FeatureValueSchema[]
  graphEvidence: GraphEvidenceSchema[]
}

export interface ModelInfo {
  modelId: string
  modelVersion?: string
  version?: string
  algorithm: string
  modelType?: string
  description?: string
  features?: string[]
  isDefault?: boolean
  isExecutable?: boolean
  trainingCompletedAt?: string
}

export interface HealthResponse {
  status: string
  version: string
  databaseStatus?: string
  modelsAvailable?: string[]
  uptime?: number
  timestamp?: string
}

export interface AlertItemDto {
  alertId: string
  analysisId: string
  datasetId: string
  entityId: string
  entityType: string
  transactionId?: string
  alertType: string
  severity: string
  priority: string
  riskScore: number
  behaviorType?: string
  triggerSource?: string
  triggerReason?: string
  status: string
  createdAt?: string
  metadata?: Record<string, unknown>
}

