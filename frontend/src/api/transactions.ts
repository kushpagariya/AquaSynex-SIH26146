import { apiData, apiFetch, buildQuery } from "./client"
import type { ApiResponse, TransactionDetail, TransactionSummary } from "./types"

export interface ListTransactionsParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortDir?: "asc" | "desc"
  riskLevel?: string
  minRiskScore?: number
  maxRiskScore?: number
  fromTimestamp?: string
  toTimestamp?: string
  minValueBtc?: string
  maxValueBtc?: string
  analysisId?: string
}

export function listTransactions(
  datasetId: string,
  params?: ListTransactionsParams,
): Promise<ApiResponse<TransactionSummary[]>> {
  return apiFetch<TransactionSummary[]>(
    `/api/datasets/${datasetId}/transactions${buildQuery(params as Record<string, unknown>)}`,
  )
}

export function getTransaction(
  transactionId: string,
  analysisId?: string,
): Promise<TransactionDetail> {
  return apiData<TransactionDetail>(
    `/api/transactions/${transactionId}${buildQuery({ analysisId })}`,
  )
}
