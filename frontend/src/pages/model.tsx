import { useEffect, useState } from "react"
import {
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
  Layers,
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
    <AppLayout title="Model Registry">
      <div className="space-y-6 font-sans">
        {/* Editorial Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-line pb-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-fg">
              Model Registry & Architecture
            </h1>
            <p className="text-xs text-fg-muted mt-1">
              Production ML specification: Supervised XGBoost binary risk detector and CatBoost 11-class typology attribution engine.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 text-xs font-medium rounded bg-[#EAF3EE] text-[#2F6B4F] border border-[#C5DECF] flex items-center gap-1">
              <CheckCircle2 className="size-3.5" />
              Artifacts Verified
            </span>
            <button
              onClick={loadModelData}
              disabled={loading}
              className="flex items-center gap-1.5 rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg-muted hover:text-accent hover:border-gray-300 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn("size-3.5", loading && "animate-spin text-accent")} />
              Refresh
            </button>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && <LoadingState label="Loading model registry specifications" />}
        {errorMsg && <ErrorState title="Failed to load model insights" description={errorMsg} />}

        {data && (
          <>
            {/* Dual Model Registry Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* XGBoost Binary Model */}
              <Panel>
                <PanelHeader
                  title="XGBoost Binary Risk Detector"
                  subtitle="Supervised transaction-level binary detector with TreeSHAP"
                  icon={<Gauge className="size-4" />}
                  action={
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-accent-soft text-accent border border-accent/20">
                      {data.binaryModel.algorithm} {data.binaryModel.version}
                    </span>
                  }
                />
                <PanelBody className="space-y-4 text-xs font-sans">
                  <p className="text-fg-muted leading-relaxed">
                    Evaluates individual transactions against 46 canonical features to generate calibrated risk probability <code className="font-mono text-fg font-semibold">P(illicit) ∈ [0, 1]</code>.
                  </p>
                  <div className="grid grid-cols-2 gap-3 pt-3 border-t border-line">
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Release Tag</span>
                      <span className="text-fg font-semibold">{data.binaryModel.releaseTag}</span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Training Target</span>
                      <span className="text-fg font-semibold">Transaction-Level Binary</span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Optimal F1 Score</span>
                      <span className="text-[#2F6B4F] font-bold font-mono">
                        {data.binaryModel.operatingPoints.f1Optimal.testF1.toFixed(4)} (τ = {data.binaryModel.operatingPoints.f1Optimal.threshold.toFixed(2)})
                      </span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">ROC-AUC / PR-AUC</span>
                      <span className="text-fg font-bold font-mono">
                        {data.binaryModel.generalization.testRocAuc.toFixed(3)} / {data.binaryModel.generalization.testPrAuc.toFixed(3)}
                      </span>
                    </div>
                  </div>
                </PanelBody>
              </Panel>

              {/* CatBoost Multiclass Model */}
              <Panel>
                <PanelHeader
                  title="CatBoost 11-Class Typology Classifier"
                  subtitle="Supervised multi-class behavioral attribution engine"
                  icon={<Layers className="size-4" />}
                  action={
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-accent-soft text-accent border border-accent/20">
                      {data.multiclassModel.algorithm} {data.multiclassModel.version}
                    </span>
                  }
                />
                <PanelBody className="space-y-4 text-xs font-sans">
                  <p className="text-fg-muted leading-relaxed">
                    Partitions flagged transactions into 11 canonical behavioral typologies (peeling chains, rapid multi-hop, coordinated bursts, mixing patterns, etc.).
                  </p>
                  <div className="grid grid-cols-2 gap-3 pt-3 border-t border-line">
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Typology Classes</span>
                      <span className="text-fg font-semibold font-mono">{data.multiclassModel.classesCount} Canonical Motifs</span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Benchmark Accuracy</span>
                      <span className="text-[#2F6B4F] font-bold font-mono">{(data.multiclassModel.accuracy * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Macro F1 Score</span>
                      <span className="text-[#2F6B4F] font-bold font-mono">{(data.multiclassModel.macroF1 * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="text-fg-subtle block text-[10px] uppercase font-semibold">Feature Dimension</span>
                      <span className="text-fg font-bold font-mono">46 Features</span>
                    </div>
                  </div>
                </PanelBody>
              </Panel>
            </div>

            {/* Scope & Terminology Notice */}
            <div className="rounded border border-line bg-panel p-4 shadow-sm text-xs font-sans space-y-1">
              <div className="font-bold text-fg flex items-center gap-2">
                <ShieldCheck className="size-4 text-accent" />
                Deterministic Scoring & Transaction-Level Scope
              </div>
              <p className="text-fg-muted leading-relaxed">
                The XGBoost binary model evaluates transactions individually. Entity and cluster risk scores reflect the{" "}
                <strong className="text-fg font-semibold">Aggregate ML Risk from Associated Transactions</strong> computed deterministically across member UTXOs, preserving full mathematical fidelity to the transaction-level classifier.
              </p>
            </div>

            {/* Operating Thresholds Table */}
            <Panel>
              <PanelHeader
                title="Operational Thresholds & Calibration"
                subtitle="Tunable operating points for balancing investigation false positive rates"
                icon={<Sliders className="size-4" />}
                action={
                  <span className="text-xs font-sans text-fg-muted">
                    Active Operational Threshold: <strong className="font-mono text-accent">τ = 0.32</strong>
                  </span>
                }
              />
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left font-sans text-xs">
                  <thead>
                    <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                      <th className="px-5 py-3 font-sans">Threshold (τ)</th>
                      <th className="px-4 py-3 font-sans">Operating Point</th>
                      <th className="px-4 py-3 font-sans text-right">Precision (Test)</th>
                      <th className="px-4 py-3 font-sans text-right">Recall (Test)</th>
                      <th className="px-4 py-3 font-sans text-right">F1 Score</th>
                      <th className="px-4 py-3 font-sans">Operational Trade-off</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {operatingPointsList.map((item) => (
                      <tr
                        key={item.point.threshold}
                        className={cn(
                          "transition-colors",
                          item.isDefault ? "bg-accent-soft/30 font-medium" : "hover:bg-panel-2",
                        )}
                      >
                        <td className="px-5 py-3.5 font-mono font-bold text-xs">
                          <div className="flex items-center gap-2">
                            <span className="text-accent">{item.point.threshold.toFixed(2)}</span>
                            {item.isDefault && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-accent text-white uppercase tracking-wider">
                                ACTIVE
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 font-semibold text-fg">{item.label}</td>
                        <td className="px-4 py-3.5 text-right font-mono font-bold text-[#2F6B4F]">
                          {(item.point.testPrecision * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono font-bold text-accent">
                          {(item.point.testRecall * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono font-bold text-fg">
                          {item.point.testF1.toFixed(4)}
                        </td>
                        <td className="px-4 py-3.5 text-fg-muted max-w-xs">{item.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            {/* 46 Canonical Predictive Features - 6 Feature Groups */}
            <Panel>
              <PanelHeader
                title="Canonical Feature Space (46 Features)"
                subtitle="Engineered feature groups spanning transaction dynamics, temporal rolling windows, and relational graph motifs"
                icon={<Layers className="size-4" />}
                action={
                  <span className="text-xs font-sans text-fg-muted font-medium">
                    6 Feature Groups • 46 Predictors
                  </span>
                }
              />
              <PanelBody className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data.featureGroups.map((group) => {
                    const Icon = groupIcons[group.name] || Layers
                    const isSelected = selectedGroup === group.name
                    return (
                      <div
                        key={group.name}
                        onClick={() => setSelectedGroup(isSelected ? null : group.name)}
                        className={cn(
                          "p-4 rounded border transition-all cursor-pointer font-sans",
                          isSelected
                            ? "border-accent bg-accent-soft/40 shadow-sm"
                            : "border-line bg-panel hover:border-gray-300",
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className="size-4 text-accent" />
                            <span className="font-bold text-xs text-fg">{group.name}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold font-mono bg-panel-2 text-fg-muted border border-line">
                            {group.count}
                          </span>
                        </div>
                        <p className="text-xs text-fg-muted mt-2 leading-relaxed">
                          {group.description}
                        </p>
                        <div className="mt-3 pt-2 border-t border-line-soft">
                          <div className="text-[10px] font-semibold text-fg-subtle uppercase tracking-wider mb-1.5">
                            Sample Features ({group.features.length})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {group.features.map((feat) => (
                              <code
                                key={feat}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-panel-2 border border-line-soft text-fg-muted font-mono"
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
              </PanelBody>
            </Panel>

            {/* Top SHAP Global Feature Importance */}
            <Panel>
              <PanelHeader
                title="Top SHAP Global Feature Importance"
                subtitle="TreeSHAP explainability weights identifying primary risk attribution drivers"
                icon={<BarChart3 className="size-4" />}
              />
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left font-sans text-xs">
                  <thead>
                    <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                      <th className="px-5 py-3 font-sans w-12">Rank</th>
                      <th className="px-4 py-3 font-sans">Feature Identifier</th>
                      <th className="px-4 py-3 font-sans">Domain Group</th>
                      <th className="px-4 py-3 font-sans w-48">Mean |SHAP| Weight</th>
                      <th className="px-4 py-3 font-sans">Attributed Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {data.topShapFeatures.map((feat) => (
                      <tr key={feat.featureName} className="hover:bg-panel-2 transition-colors">
                        <td className="px-5 py-3 font-mono font-bold text-fg-muted">#{feat.rank}</td>
                        <td className="px-4 py-3 font-mono font-semibold text-fg">
                          <code>{feat.featureName}</code>
                        </td>
                        <td className="px-4 py-3 text-fg-muted">
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-panel-2 border border-line">
                            {feat.group}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-28 h-2 bg-panel-2 rounded-full overflow-hidden border border-line-soft">
                              <div
                                className="h-full bg-accent rounded-full"
                                style={{ width: `${feat.importance * 100}%` }}
                              />
                            </div>
                            <span className="font-mono text-xs font-bold text-fg tabular-nums">{feat.importance.toFixed(3)}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-semibold border uppercase tracking-wider",
                              feat.direction === "increases_risk"
                                ? "bg-[#FDF0F0] text-[#A63D3D] border-[#F4BCBC]"
                                : feat.direction === "decreases_risk"
                                  ? "bg-[#EAF3EE] text-[#2F6B4F] border-[#C5DECF]"
                                  : "bg-panel-2 text-fg-muted border-line",
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
              </div>
            </Panel>

            {/* Benchmark Disclaimer Card */}
            <div className="rounded-lg border border-line bg-panel p-5 space-y-2 text-xs font-sans shadow-sm">
              <div className="flex items-center gap-2 text-fg font-bold">
                <CheckCircle2 className="size-4 text-[#2F6B4F]" />
                Benchmark Provenance & Offline Model Registry
              </div>
              <p className="text-fg-muted leading-relaxed">
                {data.scientificDisclaimer}
              </p>
              <div className="text-[11px] text-fg-subtle pt-3 border-t border-line flex flex-wrap gap-4 font-mono">
                <span>Binary Model: <code className="text-fg font-semibold">models/aquasynex_xgb_binary_v1.json</code></span>
                <span>Typology Model: <code className="text-fg font-semibold">models/aquasynex_catboost_multiclass_v1.cbm</code></span>
                <span>Metadata: <code className="text-fg font-semibold">models/model_metadata.json</code></span>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
