import { apiData } from "./client"
import type { AnalysisSummary } from "./types"

export function getAnalysis(analysisId: string): Promise<AnalysisSummary> {
  return apiData<AnalysisSummary>(`/api/analyses/${analysisId}`)
}
