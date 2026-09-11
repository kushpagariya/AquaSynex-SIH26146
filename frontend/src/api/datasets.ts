import { apiData, apiFetch, buildQuery } from "./client"
import type {
  AnalysisSummary,
  AnalysisTriggerResponse,
  ApiResponse,
  DatasetDetail,
  DatasetSummary,
  DatasetUploadResponse,
} from "./types"

export interface ListDatasetsParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortDir?: "asc" | "desc"
}

export function listDatasets(params?: ListDatasetsParams): Promise<ApiResponse<DatasetSummary[]>> {
  return apiFetch<DatasetSummary[]>(`/api/datasets${buildQuery(params as Record<string, unknown>)}`)
}

export function getDataset(datasetId: string): Promise<DatasetDetail> {
  return apiData<DatasetDetail>(`/api/datasets/${datasetId}`)
}

export async function uploadDataset(file: File, name: string): Promise<DatasetUploadResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("name", name)

  return apiData<DatasetUploadResponse>("/api/datasets/upload", {
    method: "POST",
    body: formData,
  })
}

export function deleteDataset(datasetId: string): Promise<{ datasetId: string; deleted: boolean }> {
  return apiData<{ datasetId: string; deleted: boolean }>(`/api/datasets/${datasetId}`, {
    method: "DELETE",
  })
}

export function triggerAnalysis(
  datasetId: string,
  payload?: { modelId?: string; modelVersion?: string; config?: Record<string, unknown> },
): Promise<AnalysisTriggerResponse> {
  return apiData<AnalysisTriggerResponse>(`/api/datasets/${datasetId}/analyses`, {
    method: "POST",
    body: JSON.stringify(payload || {}),
  })
}

export function listAnalysesForDataset(datasetId: string): Promise<AnalysisSummary[]> {
  return apiData<AnalysisSummary[]>(`/api/datasets/${datasetId}/analyses`)
}
