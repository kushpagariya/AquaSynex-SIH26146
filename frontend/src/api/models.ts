import { apiData } from "./client"
import type { ModelInfo } from "./types"

export function listModels(): Promise<ModelInfo[]> {
  return apiData<ModelInfo[]>("/api/models")
}
