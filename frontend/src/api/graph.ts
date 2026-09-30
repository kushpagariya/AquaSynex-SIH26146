import { apiData, buildQuery } from "./client"
import type { GraphExport } from "./types"

export interface GetAnalysisGraphParams {
  minRiskScore?: number
  maxNodes?: number
  includeNeighbors?: boolean
}

export function getAnalysisGraph(
  analysisId: string,
  params?: GetAnalysisGraphParams,
): Promise<GraphExport> {
  return apiData<GraphExport>(
    `/api/analyses/${analysisId}/graph${buildQuery(params as Record<string, unknown>)}`,
  )
}

export interface GetAddressSubgraphParams {
  hops?: number
  analysisId?: string
}

export function getAddressSubgraph(
  addressId: string,
  params?: GetAddressSubgraphParams,
): Promise<GraphExport> {
  return apiData<GraphExport>(
    `/api/addresses/${addressId}/graph${buildQuery(params as Record<string, unknown>)}`,
  )
}

export interface GetGraphNeighborhoodParams {
  analysisId?: string
  datasetId?: string
  entityType?: string
  depth?: number
  highRiskOnly?: boolean
}

export function getGraphNeighborhood(
  entityId: string,
  params?: GetGraphNeighborhoodParams,
): Promise<GraphExport> {
  return apiData<GraphExport>(
    `/api/graph/neighborhood${buildQuery({ entityId, ...params })}`,
  )
}
