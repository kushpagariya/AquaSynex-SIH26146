import { apiData, apiFetch, buildQuery } from "./client"
import type { ApiResponse, NetworkMapResponse } from "./types"

export function getNetworkMap(
  datasetId: string,
  analysisId?: string,
): Promise<ApiResponse<NetworkMapResponse>> {
  return apiFetch<NetworkMapResponse>(
    `/api/datasets/${datasetId}/network/map${buildQuery({ analysisId })}`,
  )
}

export function getNetworkMapData(
  datasetId: string,
  analysisId?: string,
): Promise<NetworkMapResponse> {
  return apiData<NetworkMapResponse>(
    `/api/datasets/${datasetId}/network/map${buildQuery({ analysisId })}`,
  )
}
