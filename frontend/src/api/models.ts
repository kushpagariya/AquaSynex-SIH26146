import { apiData } from "./client"
import type { ModelInfo } from "./types"

export function listModels(): Promise<ModelInfo[]> {
  return apiData<ModelInfo[]>("/api/models")
}

/**
 * Fetches the static model metadata JSON file bundled in the frontend assets.
 * Used by Model Insights page to display dynamic model performance metrics.
 */
export async function getModelMetadata(): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch("/models/model_metadata.json")
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}
