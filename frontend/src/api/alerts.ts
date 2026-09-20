import { apiData, apiFetch, buildQuery } from "./client"
import type { AlertDTO, AlertsSummaryDTO, ApiResponse } from "./types"

export interface ListAlertsParams {
  analysisId?: string
  datasetId?: string
  status?: string
  severity?: string
  alertType?: string
  priority?: string
  minRiskScore?: number
  search?: string
  page?: number
  pageSize?: number
  sortBy?: string
  sortDir?: "asc" | "desc"
}

export function listAlerts(
  params?: ListAlertsParams,
): Promise<ApiResponse<AlertDTO[]>> {
  return apiFetch<AlertDTO[]>(
    `/api/alerts${buildQuery(params as Record<string, unknown>)}`,
  )
}

export function getAlert(alertId: string): Promise<AlertDTO> {
  return apiData<AlertDTO>(`/api/alerts/${encodeURIComponent(alertId)}`)
}

export function updateAlertStatus(
  alertId: string,
  status: string,
): Promise<AlertDTO> {
  return apiData<AlertDTO>(`/api/alerts/${encodeURIComponent(alertId)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  })
}

export function updateAlertPriority(
  alertId: string,
  priority: string,
): Promise<AlertDTO> {
  return apiData<AlertDTO>(`/api/alerts/${encodeURIComponent(alertId)}/priority`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ priority }),
  })
}

export function getAlertsSummary(
  analysisId?: string,
  datasetId?: string,
): Promise<AlertsSummaryDTO> {
  const query = buildQuery({ analysisId, datasetId })
  return apiData<AlertsSummaryDTO>(`/api/alerts/summary${query}`)
}
