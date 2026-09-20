import { apiData, buildQuery } from "./client"
import type { AlertItemDto } from "./types"

export interface ListAlertsParams {
  datasetId?: string
  analysisId?: string
  status?: string
  entityId?: string
  entityType?: string
  limit?: number
}

/**
 * Retrieve persistent alerts from the backend.
 */
export async function listAlerts(params?: ListAlertsParams): Promise<AlertItemDto[]> {
  const qs = buildQuery(params as Record<string, unknown>)
  return apiData<AlertItemDto[]>(`/alerts${qs}`)
}
