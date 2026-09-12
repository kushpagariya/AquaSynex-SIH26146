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
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { getDatasetInfo, uploadAndAnalyzeDataset } from "@/data/service"
import { listModels, type ModelInfo } from "@/api"
import type { DatasetInfo, DatasetStage } from "@/data/types"
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
  const inputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    getDatasetInfo().then(setExisting).catch(() => setExisting(null))
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
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <Panel>
            <PanelHeader
              title="Ingest Dataset"
              subtitle="Load a transaction / network dataset for offline analysis"
              icon={<UploadCloud className="size-4" />}
            />
            <PanelBody>
              <div className="mb-5 rounded-md border border-line bg-panel-2 p-3.5">
                <label htmlFor="model-select" className="mb-1.5 block text-xs font-medium text-fg">
                  ML Analysis Model
                </label>
                <select
                  id="model-select"
                  value={selectedModelId}
                  disabled={active}
                  onChange={(e) => setSelectedModelId(e.target.value)}
                  className="w-full rounded border border-line bg-panel px-3 py-2 text-xs font-mono-id text-fg focus:border-accent focus:outline-none disabled:opacity-60"
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
                          {isPlaceholder ? " [Placeholder - Disabled]" : ""}
                        </option>
                      )
                    })
                  ) : (
                    <>
                      <option value="aquasynex_xgb_binary_v1">
                        aquasynex_xgb_binary_v1 — XGBoost Binary Risk Detector (Production)
                      </option>
                      <option value="aquasynex_catboost_multiclass_v1">
                        aquasynex_catboost_multiclass_v1 — CatBoost Typology Attribution
                      </option>
                      <option value="aquasynex_v1">
                        aquasynex_v1 — Full Pipeline (XGBoost + CatBoost + TreeSHAP)
                      </option>
                      <option value="isolation_forest_v1" disabled>
                        isolation_forest_v1 [Placeholder - Disabled]
                      </option>
                    </>
                  )}
                </select>
                <p className="mt-1.5 text-[11px] text-fg-subtle">
                  {selectedModelId === "aquasynex_xgb_binary_v1"
                    ? "Production 71-feature XGBoost detector with TreeSHAP explanations. Predicts transaction & entity risk scores."
                    : selectedModelId === "aquasynex_catboost_multiclass_v1"
                      ? "11-class multiclass CatBoost classifier attributing illicit financial crime typologies."
                      : selectedModelId === "aquasynex_v1"
                        ? "Runs full ensemble detection: XGBoost binary scoring + CatBoost typology attribution."
                        : "Registered machine learning model."}
                </p>
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
                    "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-14 text-center transition-colors",
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
                      Drop dataset here or browse
                    </p>
                    <p className="mt-1 text-xs text-fg-subtle">
                      Supports CSV, JSON, and network-enriched exports
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="mt-1 rounded-md border border-accent/40 bg-accent-soft px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/10"
                  >
                    Select file
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
                    <div className="space-y-3 rounded-lg border border-risk-low/40 bg-risk-low-soft p-4">
                      <div className="flex items-center gap-2 text-sm font-semibold text-risk-low">
                        <FileCheck2 className="size-5" />
                        <span>Analysis Completed Successfully</span>
                      </div>
                      <p className="text-xs text-fg-subtle">
                        Dataset ingested and scored with ML model{" "}
                        <span className="font-mono-id text-fg">{selectedModelId}</span>.
                      </p>
                      {existing?.stats ? (
                        <div className="flex flex-wrap items-center gap-3 py-1 font-mono-id text-xs text-fg-muted">
                          <span>{formatNumber(existing.stats.transactions)} transactions</span>
                          <span>•</span>
                          <span>{formatNumber(existing.stats.addresses)} entities</span>
                          <span>•</span>
                          <span className="font-semibold text-risk-high">
                            {formatNumber(existing.stats.flagged)} flagged anomalies
                          </span>
                        </div>
                      ) : null}
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => navigate("/alerts")}
                          className="flex items-center gap-1.5 rounded-md border border-accent/40 bg-accent-soft px-3.5 py-1.5 text-xs font-semibold text-accent hover:bg-accent/10"
                        >
                          <Bell className="size-3.5" />
                          View Alerts
                        </button>
                        <button
                          type="button"
                          onClick={() => navigate("/investigation")}
                          className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-3.5 py-1.5 text-xs font-medium text-fg hover:bg-panel-2"
                        >
                          <Fingerprint className="size-3.5" />
                          Investigate Results
                        </button>
                        <button
                          type="button"
                          onClick={() => navigate("/dashboard")}
                          className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-3.5 py-1.5 text-xs font-medium text-fg hover:bg-panel-2"
                        >
                          <LayoutDashboard className="size-3.5" />
                          Overview
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
                  ) : stage === "failed" ? (
                    <button
                      type="button"
                      onClick={() => {
                        setStage("idle")
                        setProgress(0)
                        setFileName("")
                        setErrorMsg(null)
                      }}
                      className="text-xs font-medium text-accent hover:underline"
                    >
                      Ingest another dataset
                    </button>
                  ) : null}
                </div>
              )}
            </PanelBody>
          </Panel>
        </div>

        <div className="lg:col-span-2">
          <Panel>
            <PanelHeader
              title="Loaded Dataset"
              subtitle="Currently active in this offline session"
              icon={<Database className="size-4" />}
            />
            <PanelBody>
              {existing ? (
                <div className="space-y-4">
                  <div className="rounded-md border border-line bg-panel-2 p-3">
                    <p className="truncate font-mono-id text-sm text-fg">
                      {existing.name}
                    </p>
                    <div className="mt-1 flex items-center gap-2 text-xs text-fg-subtle">
                      <span>{formatBytes(existing.sizeBytes)}</span>
                      <span>•</span>
                      <span>{existing.format}</span>
                    </div>
                    <p className="mt-1 text-xs text-fg-subtle">
                      Uploaded {formatDateTime(existing.uploadedAt)}
                    </p>
                  </div>

                  {existing.stats ? (
                    <div className="grid grid-cols-2 gap-3">
                      <DatasetStat
                        icon={Activity}
                        label="Transactions"
                        value={formatNumber(existing.stats.transactions)}
                      />
                      <DatasetStat
                        icon={Users}
                        label="Entities"
                        value={formatNumber(existing.stats.entities)}
                      />
                      <DatasetStat
                        icon={Wallet}
                        label="Addresses"
                        value={formatNumber(existing.stats.addresses)}
                      />
                      <DatasetStat
                        icon={Blocks}
                        label="Blocks"
                        value={formatNumber(existing.stats.blocks)}
                      />
                      <DatasetStat
                        icon={Flag}
                        label="Flagged"
                        value={formatNumber(existing.stats.flagged)}
                        accent
                      />
                      <DatasetStat
                        icon={CalendarRange}
                        label="Span"
                        value={existing.stats.span || "—"}
                      />
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-fg-subtle">No dataset loaded.</p>
              )}
            </PanelBody>
          </Panel>
        </div>
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
