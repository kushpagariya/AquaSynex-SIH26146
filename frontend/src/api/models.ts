import { apiData } from "./client"
import type { ModelInfo } from "./types"

export function listModels(): Promise<ModelInfo[]> {
  return apiData<ModelInfo[]>("/api/models")
}

/**
 * Fetches frozen production ML model metadata and specifications from backend.
 * Used by Model Insights page to display dynamic model performance metrics.
 */
export async function getModelMetadata(): Promise<Record<string, unknown> | null> {
  try {
    return await apiData<Record<string, unknown>>("/api/models/metadata")
  } catch {
    return null
  }
}
