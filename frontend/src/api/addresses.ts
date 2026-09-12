import { apiData, apiFetch, buildQuery } from "./client"
import type { AddressDetail, AddressSummary, ApiResponse } from "./types"

export interface ListAddressesParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortDir?: "asc" | "desc"
  riskLevel?: string
  minRiskScore?: number
  maxRiskScore?: number
  analysisId?: string
}

export function listAddresses(
  datasetId: string,
  params?: ListAddressesParams,
): Promise<ApiResponse<AddressSummary[]>> {
  return apiFetch<AddressSummary[]>(
    `/api/datasets/${datasetId}/addresses${buildQuery(params as Record<string, unknown>)}`,
  )
}

export function getAddress(addressId: string, analysisId?: string): Promise<AddressDetail> {
  return apiData<AddressDetail>(`/api/addresses/${addressId}${buildQuery({ analysisId })}`)
}
