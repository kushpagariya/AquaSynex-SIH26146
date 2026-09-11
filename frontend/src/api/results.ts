import { apiData, apiFetch, buildQuery } from "./client"
import type { ApiResponse, MLResultDetail, MLResultSummary } from "./types"

export interface ListResultsParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortDir?: "asc" | "desc"
  riskLevel?: string
  minRiskScore?: number
  entityType?: string
}

export function listAnalysisResults(
  analysisId: string,
  params?: ListResultsParams,
): Promise<ApiResponse<MLResultSummary[]>> {
  return apiFetch<MLResultSummary[]>(
    `/api/analyses/${analysisId}/results${buildQuery(params as Record<string, unknown>)}`,
  )
}

export function getEntityResultDetail(
  analysisId: string,
  entityId: string,
): Promise<MLResultDetail> {
  return apiData<MLResultDetail>(`/api/analyses/${analysisId}/results/${entityId}`)
}
