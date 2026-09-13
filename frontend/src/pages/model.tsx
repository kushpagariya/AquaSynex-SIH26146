import { useEffect, useState } from "react"
import {
  Cpu,
  Layers,
  Gauge,
  Sliders,
  ShieldCheck,
  CheckCircle2,
  BarChart3,
  Network,
  Clock,
  Coins,
  History,
  GitBranch,
  RefreshCw,
  Lock,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { LoadingState, ErrorState } from "@/components/ui/states"
import { getModelInsights } from "@/data/service"
import type { ModelInsightsData, ModelOperatingPoint } from "@/data/types"
import { cn } from "@/lib/utils"

export function ModelPage() {
  const [data, setData] = useState<ModelInsightsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)

  function loadModelData() {
    setLoading(true)
    setErrorMsg(null)
    getModelInsights()
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load model insights")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadModelData()
  }, [])

  const groupIcons: Record<string, typeof Coins> = {
    Transaction: Coins,
    "Address History": History,
    Temporal: Clock,
    Network: Network,
    Relational: GitBranch,
    "Historical Graph": Layers,
  }

  const operatingPointsList: Array<{
    point: ModelOperatingPoint
    label: string
    isDefault: boolean
    description: string
  }> = data
    ? [
        {
          point: data.binaryModel.operatingPoints.f1Optimal,
          label: "F1-Score Optimal (Balanced Prioritization)",
          isDefault: true,
          description: "Maximizes harmonic mean of precision and recall. Primary operating point in forensic queue.",
        },
        {
          point: data.binaryModel.operatingPoints.defaultPoint,
          label: "Standard Probability Midpoint (0.50)",
          isDefault: false,
          description: "Standard decision boundary with conservative classification.",
        },
        {
          point: data.binaryModel.operatingPoints.highPrecisionR95,
          label: "High Precision (>= 95% Precision)",
          isDefault: false,
          description: "Strict threshold for high-confidence alert dispatch with minimal false positives.",
        },
      ]
    : []

  return (
    <AppLayout title="Model Insights">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-terminal-cyan uppercase tracking-wider">
                FORENSIC ML ENGINE SPECIFICATION // READ-ONLY TERMINAL
              </span>
            </div>
            <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground flex items-center gap-3">
              <Cpu className="h-6 w-6 text-terminal-cyan" />
              Model Insights & Architecture
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Frozen dual-model architecture: XGBoost binary risk scoring and CatBoost multiclass typology classification across 46 canonical features.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 text-xs font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <Lock className="h-3 w-3" />
              Weights Frozen
            </span>
            <button
              onClick={loadModelData}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-mono bg-panel border border-border rounded hover:border-terminal-cyan transition-colors flex items-center gap-1.5 text-foreground disabled:opacity-50"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin text-terminal-cyan")} />
              Refresh
            </button>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && <LoadingState label="Loading frozen model metadata and calibration curves" />}
        {errorMsg && <ErrorState title="Failed to load model insights" description={errorMsg} />}

        {data && (
          <>
            {/* Dual Model Specification Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* XGBoost Binary Model */}
              <Panel>
                <PanelHeader
                  title={<span className="font-mono font-bold text-foreground">Transaction Risk Engine</span>}
                  icon={<Gauge className="h-4 w-4 text-terminal-cyan" />}
                  action={
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-terminal-cyan/10 text-terminal-cyan border border-terminal-cyan/30">
                      {data.binaryModel.algorithm} {data.binaryModel.version}
                    </span>
                  }
                />
                <PanelBody className="space-y-3 font-mono text-xs">
                  <p className="text-muted-foreground leading-relaxed">
                    Evaluates individual transactions to predict the probability of illicit laundering behavior. Generates a calibrated risk score <code className="text-terminal-cyan">P(illicit) ∈ [0, 1]</code>.
                  </p>
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/60">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Release Tag</span>
                      <span className="text-foreground font-bold">{data.binaryModel.releaseTag}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Training Target</span>
                      <span className="text-foreground font-bold">Transaction-Level Binary</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Optimal F1 Score</span>
                      <span className="text-emerald-400 font-bold">
                        {data.binaryModel.operatingPoints.f1Optimal.testF1.toFixed(4)} (τ = {data.binaryModel.operatingPoints.f1Optimal.threshold.toFixed(2)})
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">ROC-AUC / PR-AUC</span>
                      <span className="text-foreground font-bold">
                        {data.binaryModel.generalization.testRocAuc.toFixed(3)} / {data.binaryModel.generalization.testPrAuc.toFixed(3)}
                      </span>
                    </div>
                  </div>
                </PanelBody>
              </Panel>

              {/* CatBoost Multiclass Model */}
              <Panel>
                <PanelHeader
                  title={<span className="font-mono font-bold text-foreground">Typology Classifier</span>}
                  icon={<Layers className="h-4 w-4 text-purple-400" />}
                  action={
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/30">
                      {data.multiclassModel.algorithm} {data.multiclassModel.version}
                    </span>
                  }
                />
                <PanelBody className="space-y-3 font-mono text-xs">
                  <p className="text-muted-foreground leading-relaxed">
                    Partitions flagged transactions into 11 canonical behavioral typologies (peeling chains, rapid multi-hop, coordinated bursts, mixing patterns, etc.).
                  </p>
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/60">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Typology Classes</span>
                      <span className="text-purple-400 font-bold">{data.multiclassModel.classesCount} Canonical Motifs</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Benchmark Accuracy</span>
                      <span className="text-emerald-400 font-bold">{(data.multiclassModel.accuracy * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Macro F1 Score</span>
                      <span className="text-emerald-400 font-bold">{(data.multiclassModel.macroF1 * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase">Feature Space</span>
                      <span className="text-foreground font-bold">46 Engineered Features</span>
                    </div>
                  </div>
                </PanelBody>
              </Panel>
            </div>

            {/* Crucial Scope & Terminology Notice */}
            <div className="p-3.5 bg-panel border-l-4 border-l-terminal-cyan border-border rounded text-xs space-y-1">
              <div className="font-bold text-foreground font-mono flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-terminal-cyan" />
                CRITICAL FORENSIC SCOPE & AGGREGATE RISK SPECIFICATION
              </div>
              <p className="text-muted-foreground leading-relaxed">
                <span className="text-foreground font-semibold">Transaction-Level Scope:</span> The XGBoost binary model evaluates transactions individually. It does <span className="underline font-semibold text-foreground">not</span> directly output entity-level risk. When entity or cluster risk is displayed in the terminal, it represents an <span className="text-terminal-cyan font-bold">Aggregate ML Risk from Associated Transactions</span> computed deterministically across member UTXOs, preserving full mathematical fidelity to the transaction-level classifier.
              </p>
            </div>

            {/* Operating Thresholds & Calibration Table */}
            <Panel>
              <PanelHeader
                title={<span className="font-mono font-bold text-foreground">Decision Boundaries & Operating Points</span>}
                icon={<Sliders className="h-4 w-4 text-terminal-cyan" />}
                action={
                  <span className="text-xs font-mono text-muted-foreground">
                    Active Operational Threshold: <code className="text-terminal-cyan font-bold">τ = 0.32</code>
                  </span>
                }
              />
              <PanelBody className="p-0 overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border bg-muted/20 text-muted-foreground">
                      <th className="text-left py-3 px-4 uppercase">Threshold (τ)</th>
                      <th className="text-left py-3 px-4 uppercase">Operational Objective</th>
                      <th className="text-right py-3 px-4 uppercase">Precision (Test)</th>
                      <th className="text-right py-3 px-4 uppercase">Recall (Test)</th>
                      <th className="text-right py-3 px-4 uppercase">F1 Score</th>
                      <th className="text-left py-3 px-4 uppercase">Description & Trade-off</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {operatingPointsList.map((item) => (
                      <tr
                        key={item.point.threshold}
                        className={cn(
                          "transition-colors",
                          item.isDefault ? "bg-terminal-cyan/5 hover:bg-terminal-cyan/10" : "hover:bg-muted/10",
                        )}
                      >
                        <td className="py-3 px-4 font-bold">
                          <div className="flex items-center gap-2">
                            <span className="text-terminal-cyan text-sm">{item.point.threshold.toFixed(2)}</span>
                            {item.isDefault && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-terminal-cyan/20 text-terminal-cyan border border-terminal-cyan/40">
                                ACTIVE
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-bold text-foreground">{item.label}</td>
                        <td className="py-3 px-4 text-right font-bold text-emerald-400">
                          {(item.point.testPrecision * 100).toFixed(2)}%
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-cyan-400">
                          {(item.point.testRecall * 100).toFixed(2)}%
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-foreground">
                          {item.point.testF1.toFixed(4)}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground max-w-xs">{item.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </PanelBody>
            </Panel>

            {/* 46 Canonical Predictive Features - Exact Approved Taxonomy */}
            <Panel>
              <PanelHeader
                title={<span className="font-mono font-bold text-foreground">Canonical Feature Space (46 Features)</span>}
                icon={<Layers className="h-4 w-4 text-terminal-cyan" />}
                action={
                  <span className="px-2 py-0.5 rounded bg-muted/40 text-foreground font-bold font-mono text-xs">
                    6 Feature Groups // 46 Canonical Predictors
                  </span>
                }
              />
              <PanelBody className="space-y-4">
                <p className="text-xs text-muted-foreground font-mono">
                  The models ingest exactly 46 engineered features spanning on-chain UTXO dynamics, historical entity habits, temporal timing, network broadcast telemetry, multi-entity relationships, and graph network metrics.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.featureGroups.map((group) => {
                    const Icon = groupIcons[group.name] || Layers
                    const isSelected = selectedGroup === group.name
                    return (
                      <div
                        key={group.name}
                        onClick={() => setSelectedGroup(isSelected ? null : group.name)}
                        className={cn(
                          "p-3.5 rounded border transition-all cursor-pointer font-mono",
                          isSelected
                            ? "bg-panel border-terminal-cyan shadow-sm"
                            : "bg-panel/60 border-border hover:border-border/90",
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4 text-terminal-cyan" />
                            <span className="font-bold text-sm text-foreground">{group.name}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-muted/60 text-terminal-cyan border border-border">
                            {group.count} {group.count === 1 ? "feature" : "features"}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
                          {group.description}
                        </p>
                        <div className="mt-3 pt-2 border-t border-border/60">
                          <div className="text-[10px] text-muted-foreground uppercase mb-1">
                            Sample Predictors ({group.features.length})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {group.features.map((feat) => (
                              <code
                                key={feat}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-background border border-border/60 text-muted-foreground"
                              >
                                {feat}
                              </code>
                            ))}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Taxonomy Verification Footnote */}
                <div className="p-2.5 bg-background border border-border rounded text-[11px] font-mono text-muted-foreground flex items-center justify-between">
                  <span>
                    Canonical Taxonomy: Transaction (15) + Address History (8) + Temporal (7) + Network (6: 4 numeric, 2 categorical) + Relational (4) + Historical Graph (6)
                  </span>
                  <span className="font-bold text-terminal-cyan">Total = 46 Features</span>
                </div>
              </PanelBody>
            </Panel>

            {/* SHAP Feature Importance Table */}
            <Panel>
              <PanelHeader
                title={<span className="font-mono font-bold text-foreground">Top SHAP Global Feature Importance</span>}
                icon={<BarChart3 className="h-4 w-4 text-terminal-cyan" />}
                action={<span className="text-xs font-mono text-muted-foreground">TreeSHAP Explainability</span>}
              />
              <PanelBody className="p-0 overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-border bg-muted/20 text-muted-foreground">
                      <th className="text-left py-2.5 px-4 uppercase w-12">Rank</th>
                      <th className="text-left py-2.5 px-4 uppercase">Feature Symbol</th>
                      <th className="text-left py-2.5 px-4 uppercase">Domain Group</th>
                      <th className="text-left py-2.5 px-4 uppercase w-48">Mean |SHAP| Weight</th>
                      <th className="text-left py-2.5 px-4 uppercase">Impact Direction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {data.topShapFeatures.map((feat) => (
                      <tr key={feat.featureName} className="hover:bg-muted/10 transition-colors">
                        <td className="py-2.5 px-4 font-bold text-muted-foreground">#{feat.rank}</td>
                        <td className="py-2.5 px-4 font-bold text-foreground">
                          <code>{feat.featureName}</code>
                        </td>
                        <td className="py-2.5 px-4 text-muted-foreground">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-muted/40 border border-border">
                            {feat.group}
                          </span>
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="flex items-center gap-2">
                            <div className="w-28 h-2 bg-background rounded-full overflow-hidden border border-border/60">
                              <div
                                className="h-full bg-terminal-cyan"
                                style={{ width: `${feat.importance * 100}%` }}
                              />
                            </div>
                            <span className="text-terminal-cyan font-bold">{feat.importance.toFixed(3)}</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-bold border",
                              feat.direction === "increases_risk"
                                ? "bg-severity-high/10 text-severity-high border-severity-high/30"
                                : feat.direction === "decreases_risk"
                                  ? "bg-severity-low/10 text-severity-low border-severity-low/30"
                                  : "bg-muted/30 text-muted-foreground border-border",
                            )}
                          >
                            {feat.direction === "increases_risk"
                              ? "Increases Risk"
                              : feat.direction === "decreases_risk"
                                ? "Decreases Risk"
                                : "Neutral"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </PanelBody>
            </Panel>

            {/* Benchmark Disclaimer Card */}
            <div className="p-4 bg-panel border border-border rounded space-y-2 text-xs font-mono">
              <div className="flex items-center gap-2 text-foreground font-bold">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Benchmark Provenance & Deterministic Scoring
              </div>
              <p className="text-muted-foreground leading-relaxed">
                {data.scientificDisclaimer}
              </p>
              <div className="text-[10px] text-muted-foreground pt-2 border-t border-border flex flex-wrap gap-4">
                <span>Model Artifact: <code className="text-foreground">models/aquasynex_xgb_binary_v1.json</code></span>
                <span>Multiclass Artifact: <code className="text-foreground">models/aquasynex_catboost_multiclass_v1.cbm</code></span>
                <span>Metadata: <code className="text-foreground">models/model_metadata.json</code></span>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
