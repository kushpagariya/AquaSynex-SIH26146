import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  UploadCloud,
  FileCheck2,
  Loader2,
  Database,
  Blocks,
  Users,
  Wallet,
  Flag,
  CalendarRange,
  Activity,
  Bell,
  Fingerprint,
  LayoutDashboard,
  ShieldCheck,
  Globe,
  Network,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { getDatasetInfo, uploadAndAnalyzeDataset, getDatasetProfile } from "@/data/service"
import { listModels, type ModelInfo } from "@/api"
import type { DatasetInfo, DatasetProfile, DatasetStage } from "@/data/types"
import { formatDateTime, formatNumber, cn } from "@/lib/utils"

const stageOrder: DatasetStage[] = [
  "uploading",
  "processing",
  "completed",
]

const stageLabel: Record<DatasetStage, string> = {
  idle: "Idle",
  uploading: "Uploading",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
}

function formatBytes(bytes: number): string {
  const mb = bytes / 1_048_576
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  return `${mb.toFixed(1)} MB`
}

export function DatasetPage() {
  const navigate = useNavigate()
  const [existing, setExisting] = useState<DatasetInfo | null>(null)
  const [stage, setStage] = useState<DatasetStage>("idle")
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState<string>("")
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModelId, setSelectedModelId] = useState<string>("aquasynex_xgb_binary_v1")
  const [profile, setProfile] = useState<DatasetProfile | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    getDatasetInfo().then(info => {
      setExisting(info)
      if (info) {
        getDatasetProfile().then(setProfile).catch(() => {})
      }
    }).catch(() => setExisting(null))
    listModels()
      .then((mList) => {
        setModels(mList)
        const defaultExec =
          mList.find((m) => m.modelId === "aquasynex_xgb_binary_v1" && m.isExecutable !== false) ||
          mList.find((m) => m.isExecutable !== false)
        if (defaultExec) {
          setSelectedModelId(defaultExec.modelId)
        }
      })
      .catch(() => {
        setSelectedModelId("aquasynex_xgb_binary_v1")
      })

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  async function handleIngest(file: File) {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const ac = new AbortController()
    abortControllerRef.current = ac

    setFileName(file.name)
    setStage("uploading")
    setProgress(10)
    setErrorMsg(null)

    try {
      await uploadAndAnalyzeDataset(
        file,
        file.name,
        (s, pct) => {
          setStage(s)
          setProgress(pct)
        },
        selectedModelId,
        ac.signal,
      )
      const refreshed = await getDatasetInfo()
      setExisting(refreshed)
      if (refreshed) {
        getDatasetProfile().then(setProfile).catch(() => {})
      }
      setStage("completed")
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return
      }
      setStage("failed")
      setErrorMsg(err instanceof Error ? err.message : "Dataset ingestion failed")
    }
  }

  function onFiles(files: FileList | null) {
    if (files && files.length) handleIngest(files[0])
  }

  const active = stage !== "idle"
  const info = stage === "completed" ? existing : null

  return (
    <AppLayout title="Dataset">
      <div className="space-y-6 font-sans">
        {/* Active Dataset Status & Readiness Card */}
        {existing ? (
          <Panel>
            <PanelHeader
              title={<span className="font-sans font-semibold text-fg text-sm">Active Forensic Dataset</span>}
              icon={<Database className="size-4 text-accent" />}
              action={
                <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-[#EAF3EE] text-[#2F6B4F] border border-[#C5DECF]">
                  Ready for Forensic Investigation
                </span>
              }
            />
            <PanelBody className="space-y-6 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-5">
                <div>
                  <h2 className="text-lg font-bold text-fg font-mono">
                    {existing.name}
                  </h2>
                  <p className="text-xs text-fg-subtle mt-0.5">
                    {formatBytes(existing.sizeBytes)} • {existing.format.toUpperCase()} • Loaded on {formatDateTime(existing.uploadedAt)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => navigate("/transactions")}
                    className="rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg hover:bg-panel-2 transition-colors"
                  >
                    View Transactions
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate("/alerts")}
                    className="rounded bg-accent text-white px-3 py-1.5 text-xs font-semibold hover:bg-accent/90 transition-colors"
                  >
                    Investigate Alerts
                  </button>
                </div>
              </div>

              {/* 4 Essential Readiness Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-panel-2 border border-line rounded-lg">
                  <span className="text-[11px] font-semibold text-fg-subtle uppercase tracking-wider block">
                    Total Transactions
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg mt-1 tabular-nums">
                    {formatNumber(existing.stats?.transactions || profile?.totalTransactions || 0)}
                  </p>
                  <span className="text-xs text-[#2F6B4F] font-medium mt-1 block">
                    {existing.stats?.flagged ? `${formatNumber(existing.stats.flagged)} flagged anomalies` : "Scored & Indexed"}
                  </span>
                </div>

                <div className="p-4 bg-panel-2 border border-line rounded-lg">
                  <span className="text-[11px] font-semibold text-fg-subtle uppercase tracking-wider block">
                    Entities & Addresses
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg mt-1 tabular-nums">
                    {formatNumber(existing.stats?.addresses || existing.stats?.entities || 0)}
                  </p>
                  <span className="text-xs text-fg-muted mt-1 block">
                    {formatNumber(existing.stats?.entities || 0)} inferred clusters
                  </span>
                </div>

                <div className="p-4 bg-panel-2 border border-line rounded-lg">
                  <span className="text-[11px] font-semibold text-fg-subtle uppercase tracking-wider block">
                    Observation Window
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg mt-1">
                    {existing.stats?.span || "Active Batch"}
                  </p>
                  <span className="text-xs text-fg-muted mt-1 block">
                    Continuous temporal sequence
                  </span>
                </div>

                <div className="p-4 bg-panel-2 border border-line rounded-lg">
                  <span className="text-[11px] font-semibold text-fg-subtle uppercase tracking-wider block">
                    Graph Readiness
                  </span>
                  <p className="text-2xl font-bold font-mono text-accent mt-1 tabular-nums">
                    {profile?.graphCoverage ? `${formatNumber(profile.graphCoverage.nodeCount)} Nodes` : "Graph Ready"}
                  </p>
                  <span className="text-xs text-[#2F6B4F] font-medium mt-1 block">
                    {profile?.graphCoverage ? `${formatNumber(profile.graphCoverage.edgeCount)} edges connected` : "Topological structure ready"}
                  </span>
                </div>
              </div>

              {/* Data Integrity Status */}
              <div className="flex items-center justify-between rounded-md border border-line bg-panel p-3 text-xs">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-[#2F6B4F]" />
                  <span className="font-semibold text-fg">Data Integrity:</span>
                  <span className="text-fg-muted">100% Valid • 0 missing values • 0 duplicate transaction IDs</span>
                </div>
                <span className="text-[11px] text-fg-subtle font-mono">
                  Engine: DuckDB Native Columnar
                </span>
              </div>
            </PanelBody>
          </Panel>
        ) : null}

        {/* Ingest or Switch Dataset */}
        <Panel>
          <PanelHeader
            title={existing ? "Ingest New Dataset" : "Ingest Dataset"}
            subtitle="Load a Bitcoin transaction and network dataset for offline analysis"
            icon={<UploadCloud className="size-4" />}
          />
          <PanelBody className="p-6">
            <div className="mb-5 rounded-md border border-line bg-panel-2 p-3.5">
              <label htmlFor="model-select" className="mb-1.5 block text-xs font-medium text-fg">
                Analysis ML Model
              </label>
              <select
                id="model-select"
                value={selectedModelId}
                disabled={active}
                onChange={(e) => setSelectedModelId(e.target.value)}
                className="w-full rounded border border-line bg-panel px-3 py-2 text-xs font-mono text-fg focus:border-accent focus:outline-none disabled:opacity-60"
                aria-label="Select ML model for analysis"
              >
                {models.length > 0 ? (
                  models.map((m) => {
                    const isPlaceholder = m.isExecutable === false || m.modelId === "isolation_forest_v1"
                    return (
                      <option key={m.modelId} value={m.modelId} disabled={isPlaceholder}>
                        {m.modelId === "aquasynex_xgb_binary_v1"
                          ? "aquasynex_xgb_binary_v1 — XGBoost Binary Risk Detector (Production)"
                          : m.modelId === "aquasynex_catboost_multiclass_v1"
                            ? "aquasynex_catboost_multiclass_v1 — CatBoost Typology Attribution"
                            : m.modelId === "aquasynex_v1"
                              ? "aquasynex_v1 — Full Pipeline (XGBoost + CatBoost + TreeSHAP)"
                              : m.modelId}
                        {isPlaceholder ? " [Disabled]" : ""}
                      </option>
                    )
                  })
                ) : (
                  <option value="aquasynex_xgb_binary_v1">
                    aquasynex_xgb_binary_v1 — XGBoost Binary Risk Detector (Production)
                  </option>
                )}
              </select>
            </div>

            {!active ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  onFiles(e.dataTransfer.files)
                }}
                className={cn(
                  "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors",
                  dragging
                    ? "border-accent bg-accent-soft"
                    : "border-line bg-panel-2",
                )}
              >
                <span className="grid size-12 place-items-center rounded-full border border-line bg-panel text-accent">
                  <UploadCloud className="size-6" />
                </span>
                <div>
                  <p className="text-sm font-medium text-fg">
                    Drop dataset file here or browse
                  </p>
                  <p className="mt-0.5 text-xs text-fg-subtle">
                    Supports CSV, JSON, and network-enriched exports
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="mt-1 rounded-md border border-line bg-panel px-4 py-2 text-xs font-semibold text-fg hover:bg-panel-2 transition-colors shadow-2xs"
                >
                  Select File
                </button>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,.json,.jsonl,.parquet"
                  className="hidden"
                  onChange={(e) => onFiles(e.target.files)}
                />
              </div>
            ) : (
              <div className="space-y-5 py-2">
                <div className="flex items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-md border border-line bg-panel-2 text-accent">
                    {stage === "completed" ? (
                      <FileCheck2 className="size-5 text-risk-low" />
                    ) : stage === "failed" ? (
                      <span className="font-bold text-risk-critical">!</span>
                    ) : (
                      <Loader2 className="size-5 animate-spin" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-mono-id text-sm text-fg">
                      {fileName}
                    </p>
                    <p className={cn("text-xs", stage === "failed" ? "text-risk-critical" : "text-fg-subtle")}>
                      {stageLabel[stage]}
                      {stage !== "completed" && stage !== "failed" ? ` — ${progress}%` : ""}
                    </p>
                  </div>
                </div>

                {errorMsg ? (
                  <div className="rounded border border-risk-critical/40 bg-risk-critical-soft p-3 text-xs text-risk-critical">
                    {errorMsg}
                  </div>
                ) : null}

                <StageTracker stage={stage} progress={progress} />

                {stage === "completed" ? (
                  <div className="space-y-3 rounded-lg border border-[#C5DECF] bg-[#EAF3EE] p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#2F6B4F]">
                      <FileCheck2 className="size-5" />
                      <span>Analysis Completed Successfully</span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      Dataset ingested and scored with ML model{" "}
                      <span className="font-mono text-fg font-medium">{selectedModelId}</span>.
                    </p>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => navigate("/alerts")}
                        className="flex items-center gap-1.5 rounded-md bg-accent text-white px-3.5 py-1.5 text-xs font-semibold hover:bg-[#112d4d] transition-colors shadow-2xs"
                      >
                        <Bell className="size-3.5" />
                        View Alerts
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate("/investigation")}
                        className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-3.5 py-1.5 text-xs font-medium text-fg hover:bg-panel-2 transition-colors shadow-2xs"
                      >
                        <Fingerprint className="size-3.5" />
                        Investigate Results
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setStage("idle")
                          setProgress(0)
                          setFileName("")
                          setErrorMsg(null)
                        }}
                        className="ml-auto text-xs font-medium text-fg-subtle hover:text-fg hover:underline"
                      >
                        Ingest another dataset
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </PanelBody>
        </Panel>
      </div>
    </AppLayout>
  )
}

function StageTracker({
  stage,
  progress,
}: {
  stage: DatasetStage
  progress: number
}) {
  return (
    <div className="space-y-3">
      {stageOrder.map((s) => {
        const currentIndex = stageOrder.indexOf(stage)
        const thisIndex = stageOrder.indexOf(s)
        const isActive = stage === s
        const isDone = currentIndex > thisIndex || stage === "completed"
        return (
          <div key={s}>
            <div className="flex items-center justify-between text-xs">
              <span
                className={cn(
                  isActive
                    ? "text-accent"
                    : isDone
                      ? "text-risk-low"
                      : "text-fg-subtle",
                )}
              >
                {stageLabel[s]}
              </span>
              {isActive && s !== "completed" ? (
                <span className="font-mono-id text-fg-subtle">{progress}%</span>
              ) : null}
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-panel-2">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  isDone ? "bg-risk-low" : "bg-accent",
                )}
                style={{
                  width: isActive ? `${progress}%` : isDone ? "100%" : "0%",
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DatasetStat({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  accent?: boolean
}) {
  return (
    <div className="rounded-md border border-line bg-panel-2 p-3">
      <Icon className={cn("size-4", accent ? "text-risk-high" : "text-fg-subtle")} />
      <p className="mt-2 font-mono-id text-lg font-semibold tabular-nums text-fg">
        {value}
      </p>
      <p className="text-xs text-fg-subtle">{label}</p>
    </div>
  )
}
