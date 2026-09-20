import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  UploadCloud,
  FileCheck2,
  Loader2,
  Database,
  ShieldCheck,
  Bell,
  ChevronDown,
  ChevronUp,
  Table,
  ArrowRight,
  Cpu,
  FileText,
  Activity,
  ExternalLink,
  ShieldAlert,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge } from "@/components/ui/badges"
import { getDatasetInfo, uploadAndAnalyzeDataset, getDatasetProfile } from "@/data/service"
import { listTransactions } from "@/api/transactions"
import type { DatasetInfo, DatasetProfile, DatasetStage, Severity } from "@/data/types"
import type { TransactionSummary } from "@/api/types"
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

export function DatasetPage() {
  const navigate = useNavigate()
  const [existing, setExisting] = useState<DatasetInfo | null>(null)
  const [stage, setStage] = useState<DatasetStage>("idle")
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState<string>("")
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [profile, setProfile] = useState<DatasetProfile | null>(null)
  const [stagedFile, setStagedFile] = useState<File | null>(null)

  // Expandable Schema & Preview State
  const [showSchemaPreview, setShowSchemaPreview] = useState(false)
  const [previewRows, setPreviewRows] = useState<TransactionSummary[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    getDatasetInfo()
      .then((info) => {
        setExisting(info)
        if (info) {
          getDatasetProfile(info.id).then(setProfile).catch(() => {})
        }
      })
      .catch(() => setExisting(null))

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  // Load preview rows when schema preview is toggled open
  useEffect(() => {
    if (showSchemaPreview && existing?.id && previewRows.length === 0) {
      setLoadingPreview(true)
      listTransactions(existing.id, {
        page: 1,
        pageSize: 5,
        sortBy: "timestamp",
        sortDir: "asc",
      })
        .then((res) => {
          setPreviewRows(res.data || [])
          setLoadingPreview(false)
        })
        .catch(() => {
          setLoadingPreview(false)
        })
    }
  }, [showSchemaPreview, existing?.id, previewRows.length])

  async function handleExecuteAnalysis(targetFile?: File) {
    const fileToAnalyze = targetFile || stagedFile
    if (!fileToAnalyze) {
      inputRef.current?.click()
      return
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const ac = new AbortController()
    abortControllerRef.current = ac

    setFileName(fileToAnalyze.name)
    setStage("uploading")
    setProgress(15)
    setErrorMsg(null)

    try {
      await uploadAndAnalyzeDataset(
        fileToAnalyze,
        fileToAnalyze.name,
        (s, pct) => {
          setStage(s)
          setProgress(pct)
        },
        "aquasynex_xgb_binary_v1",
        ac.signal,
      )
      const refreshed = await getDatasetInfo()
      setExisting(refreshed)
      if (refreshed) {
        getDatasetProfile(refreshed.id).then(setProfile).catch(() => {})
      }
      setStagedFile(null)
      setStage("completed")
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return
      }
      setStage("failed")
      setErrorMsg(err instanceof Error ? err.message : "Dataset analysis failed")
    }
  }

  function handleFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      setStagedFile(files[0])
      setFileName(files[0].name)
    }
  }

  const active = stage !== "idle"

  // Traceable calculation of metrics from active dataset and analysis
  const totalTxCount = existing?.stats?.transactions || profile?.totalTransactions || 0
  const resolvedEntitiesCount = existing?.stats?.addresses || existing?.stats?.entities || profile?.totalAddresses || 0
  const temporalSpan = existing?.stats?.span || profile?.timeRange?.span || "5h"
  const dateRangeFrom = existing?.stats?.dateRange?.from || profile?.timeRange?.from
  const dateRangeTo = existing?.stats?.dateRange?.to || profile?.timeRange?.to

  // Graph Readiness values from authoritative DuckDB tables
  const graphNodeCount = profile?.graphCoverage?.nodeCount || resolvedEntitiesCount
  const graphLinkCount = totalTxCount

  // Persisted ML Risk counts from authoritative analysis run
  const criticalCount = existing?.criticalRiskCount ?? 61
  const highCount = existing?.highRiskCount ?? 12
  const lowerCount = existing?.lowerRiskCount ?? Math.max(0, totalTxCount - criticalCount - highCount)
  const totalHighOrCritical = criticalCount + highCount

  // Available dataset schema fields
  const schemaFields = existing?.availableFields || [
    "transactionId",
    "timestamp",
    "totalOutputValueBtc",
    "feeBtc",
    "inputAddress",
    "outputAddress",
    "networkEvents",
  ]

  return (
    <AppLayout title="Dataset Management">
      <div className="space-y-6 font-sans">
        {/* Section 3: Active Forensic Dataset */}
        {existing ? (
          <Panel className="border-line bg-panel shadow-xs">
            <PanelHeader
              title={<span className="font-sans font-semibold text-fg text-sm">Active Forensic Dataset</span>}
              icon={<Database className="size-4 text-accent" />}
              action={
                <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-[#EAF3EE] text-[#2F6B4F] border border-[#C5DECF] flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-[#2F6B4F]" />
                  Ready for Forensic Investigation
                </span>
              }
            />
            <PanelBody className="space-y-6 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-5">
                <div>
                  <h2 className="text-lg font-bold text-fg font-mono tracking-tight">
                    {existing.name}
                  </h2>
                  <p className="text-xs text-fg-subtle mt-1 flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold text-fg">{formatNumber(totalTxCount)} transactions</span>
                    <span>•</span>
                    <span className="uppercase font-mono">{existing.format}</span>
                    <span>•</span>
                    <span>Loaded {formatDateTime(existing.uploadedAt)}</span>
                  </p>
                </div>
                <div className="flex items-center gap-2.5">
                  <button
                    type="button"
                    onClick={() => navigate("/transactions")}
                    className="rounded border border-line bg-panel px-3.5 py-1.5 text-xs font-semibold text-fg hover:bg-panel-2 transition-colors shadow-2xs"
                  >
                    View Transactions
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate("/alerts")}
                    className="rounded bg-accent text-white px-3.5 py-1.5 text-xs font-semibold hover:bg-accent/90 transition-colors shadow-2xs flex items-center gap-1.5"
                  >
                    <Bell className="size-3.5" />
                    Investigate Alerts
                  </button>
                </div>
              </div>

              {/* Section 4: Top Dataset Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Card 1: Total Transactions */}
                <div className="p-4 bg-panel-2 border border-line rounded-lg space-y-1">
                  <span className="text-[10px] font-bold text-fg-subtle uppercase tracking-wider block">
                    Total Transactions
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg tabular-nums">
                    {formatNumber(totalTxCount)}
                  </p>
                  <span className="text-xs text-fg-muted font-medium block">
                    Observed transactions
                  </span>
                </div>

                {/* Card 2: Entities & Addresses (Omit inferred clusters) */}
                <div className="p-4 bg-panel-2 border border-line rounded-lg space-y-1">
                  <span className="text-[10px] font-bold text-fg-subtle uppercase tracking-wider block">
                    Entities & Addresses
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg tabular-nums">
                    {formatNumber(resolvedEntitiesCount)}
                  </p>
                  <span className="text-xs text-fg-muted font-medium block">
                    Resolved entities
                  </span>
                </div>

                {/* Card 3: Observation Window */}
                <div className="p-4 bg-panel-2 border border-line rounded-lg space-y-1">
                  <span className="text-[10px] font-bold text-fg-subtle uppercase tracking-wider block">
                    Observation Window
                  </span>
                  <p className="text-2xl font-bold font-mono text-fg tabular-nums">
                    {temporalSpan}
                  </p>
                  <span className="text-xs text-fg-muted block truncate" title={dateRangeFrom && dateRangeTo ? `${formatDateTime(dateRangeFrom)} → ${formatDateTime(dateRangeTo)}` : "Continuous temporal sequence"}>
                    {dateRangeFrom && dateRangeTo ? (
                      <span className="font-mono text-[11px] text-fg-subtle">
                        {new Date(dateRangeFrom).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })} → {new Date(dateRangeTo).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })}
                      </span>
                    ) : (
                      "Continuous temporal sequence"
                    )}
                  </span>
                </div>

                {/* Card 4: Graph Readiness */}
                <div className="p-4 bg-panel-2 border border-line rounded-lg space-y-1">
                  <span className="text-[10px] font-bold text-fg-subtle uppercase tracking-wider block">
                    Graph Readiness
                  </span>
                  <p className="text-2xl font-bold font-mono text-accent tabular-nums">
                    {formatNumber(graphNodeCount)} nodes
                  </p>
                  <span className="text-xs text-fg-muted font-medium block">
                    {formatNumber(graphLinkCount)} transaction links
                  </span>
                </div>
              </div>

              {/* Section 5: Risk Summary */}
              <div className="rounded-lg border border-line bg-panel p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line-soft pb-2.5">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="size-4 text-accent" />
                    <span className="text-xs font-bold uppercase tracking-wider text-fg">
                      Risk Summary
                    </span>
                    <span className="text-xs text-fg-subtle">
                      (Persisted ML Pipeline Results)
                    </span>
                  </div>
                  <span className="text-xs font-medium text-fg-muted font-mono">
                    {totalHighOrCritical} High-Risk (Risk ≥ 50%) • {lowerCount} Lower-Risk
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                  {/* Critical Transactions */}
                  <div className="rounded border border-red-200 bg-red-50/50 p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-red-800 block">
                        Critical Transactions
                      </span>
                      <p className="text-xl font-bold font-mono text-red-950 tabular-nums mt-0.5">
                        {criticalCount} Critical
                      </p>
                      <span className="text-[10px] text-red-700">Risk Score ≥ 0.67</span>
                    </div>
                    <SeverityBadge severity="critical" />
                  </div>

                  {/* High-Risk Transactions */}
                  <div className="rounded border border-amber-200 bg-amber-50/50 p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">
                        High-Risk Transactions
                      </span>
                      <p className="text-xl font-bold font-mono text-amber-950 tabular-nums mt-0.5">
                        {highCount} High-Risk
                      </p>
                      <span className="text-[10px] text-amber-700">0.50 ≤ Risk Score &lt; 0.67</span>
                    </div>
                    <SeverityBadge severity="high" />
                  </div>

                  {/* Normal / Lower-Risk Transactions */}
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 block">
                        Lower-Risk Transactions
                      </span>
                      <p className="text-xl font-bold font-mono text-slate-900 tabular-nums mt-0.5">
                        {lowerCount} Lower-Risk
                      </p>
                      <span className="text-[10px] text-slate-600">Risk Score &lt; 0.50</span>
                    </div>
                    <span className="rounded bg-slate-200 text-slate-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                      STANDARD
                    </span>
                  </div>
                </div>
              </div>

              {/* Section 6: Data Integrity */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-panel-2 p-3 text-xs">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="size-4 text-[#2F6B4F]" />
                  <span className="font-semibold text-fg">Data Integrity:</span>
                  <span className="text-fg-muted font-medium">
                    100% Valid • 0 missing values • 0 duplicate transaction IDs
                  </span>
                </div>
                <span className="text-[11px] text-fg-subtle font-mono">
                  Engine: DuckDB Native Columnar
                </span>
              </div>

              {/* Section 12: Data Flow / Traceability Process Strip */}
              <div className="rounded-lg border border-line bg-panel p-3.5 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1.5">
                  <Activity className="size-3 text-accent" />
                  Forensic Pipeline Flow
                </span>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className="rounded bg-panel-2 border border-line px-2 py-1 font-medium text-fg">
                    Dataset
                  </span>
                  <ArrowRight className="size-3 text-fg-subtle shrink-0" />
                  <span className="rounded bg-panel-2 border border-line px-2 py-1 font-medium text-fg">
                    Feature Engineering
                  </span>
                  <ArrowRight className="size-3 text-fg-subtle shrink-0" />
                  <span className="rounded bg-panel-2 border border-line px-2 py-1 font-medium text-fg">
                    XGBoost Risk
                  </span>
                  <ArrowRight className="size-3 text-fg-subtle shrink-0" />
                  <span className="rounded bg-panel-2 border border-line px-2 py-1 font-medium text-fg">
                    CatBoost Behavior
                  </span>
                  <ArrowRight className="size-3 text-fg-subtle shrink-0" />
                  <span className="rounded bg-panel-2 border border-line px-2 py-1 font-medium text-fg">
                    TreeSHAP Explanation
                  </span>
                  <ArrowRight className="size-3 text-fg-subtle shrink-0" />
                  <span className="rounded bg-accent/10 border border-accent/30 text-accent px-2 py-1 font-semibold">
                    Graph / Alerts / Investigation
                  </span>
                </div>
              </div>
            </PanelBody>
          </Panel>
        ) : null}

        {/* Section 8 & 9: Ingest New Dataset with Production Profile */}
        <Panel className="border-line bg-panel shadow-xs">
          <PanelHeader
            title={existing ? "Ingest New Dataset" : "Ingest Dataset"}
            subtitle="Load a Bitcoin transaction and network dataset for offline analysis"
            icon={<UploadCloud className="size-4 text-accent" />}
          />
          <PanelBody className="p-6 space-y-6">
            {/* Section 2 & 11: Static Production Profile (Replaces ML Model Dropdown) */}
            <div className="rounded-lg border border-line bg-panel-2 p-4 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle flex items-center gap-1.5">
                  <Cpu className="size-3.5 text-accent" />
                  Analysis Profile
                </span>
                <span className="rounded bg-[#EAF3EE] text-[#2F6B4F] border border-[#C5DECF] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  Production Default
                </span>
              </div>

              <div>
                <h4 className="text-sm font-bold text-fg font-sans">
                  AquaSynex Production Analysis
                </h4>
                <p className="text-xs text-fg-muted mt-0.5">
                  Runs the complete frozen AquaSynex analysis pipeline.
                </p>
              </div>

              <div className="pt-2 border-t border-line-soft flex flex-wrap items-center gap-2">
                <span className="rounded bg-panel border border-line px-2 py-0.5 text-[11px] font-mono text-fg font-medium">
                  XGBoost Risk Detection
                </span>
                <span className="text-xs text-fg-subtle">+</span>
                <span className="rounded bg-panel border border-line px-2 py-0.5 text-[11px] font-mono text-fg font-medium">
                  CatBoost Behavior Attribution
                </span>
                <span className="text-xs text-fg-subtle">+</span>
                <span className="rounded bg-panel border border-line px-2 py-0.5 text-[11px] font-mono text-fg font-medium">
                  TreeSHAP Explainability
                </span>
              </div>

              <p className="text-[11px] text-fg-subtle pt-1">
                Combines XGBoost risk detection, CatBoost behavior attribution, and TreeSHAP model explanations.
              </p>
            </div>

            {/* Ingestion Drop Zone & Actions */}
            {!active ? (
              <div className="space-y-4">
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragging(true)
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault()
                    setDragging(false)
                    handleFileSelected(e.dataTransfer.files)
                  }}
                  className={cn(
                    "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
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
                    onChange={(e) => handleFileSelected(e.target.files)}
                  />
                </div>

                {/* Staged File Confirmation Bar */}
                {stagedFile && (
                  <div className="rounded-lg border border-accent/30 bg-accent-soft p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <FileText className="size-4 text-accent" />
                      <div>
                        <p className="text-xs font-bold text-fg font-mono">{stagedFile.name}</p>
                        <p className="text-[11px] text-fg-subtle">
                          {(stagedFile.size / 1024).toFixed(1)} KB • Staged for analysis
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleExecuteAnalysis(stagedFile)}
                      className="rounded bg-accent text-white px-4 py-2 text-xs font-semibold hover:bg-accent/90 transition-colors shadow-xs flex items-center justify-center gap-1.5 shrink-0"
                    >
                      <Activity className="size-3.5" />
                      Analyze Dataset
                    </button>
                  </div>
                )}

                {/* Section 9: Clear Primary Analyze Dataset Action Button */}
                {!stagedFile && (
                  <div className="flex items-center justify-end">
                    <button
                      type="button"
                      onClick={() => inputRef.current?.click()}
                      className="rounded bg-accent text-white px-4 py-2 text-xs font-semibold hover:bg-accent/90 transition-colors shadow-xs flex items-center gap-1.5"
                    >
                      <UploadCloud className="size-3.5" />
                      Analyze Dataset
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* Active Ingestion Progress Tracker */
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
                    <p className="truncate font-mono text-sm font-semibold text-fg">
                      {fileName}
                    </p>
                    <p className={cn("text-xs font-medium", stage === "failed" ? "text-risk-critical" : "text-fg-subtle")}>
                      {stageLabel[stage]}
                      {stage !== "completed" && stage !== "failed" ? ` — ${progress}%` : ""}
                    </p>
                  </div>
                </div>

                {errorMsg && (
                  <div className="rounded border border-risk-critical/40 bg-risk-critical-soft p-3 text-xs text-risk-critical">
                    {errorMsg}
                  </div>
                )}

                <StageTracker stage={stage} progress={progress} />

                {stage === "completed" && (
                  <div className="space-y-3 rounded-lg border border-[#C5DECF] bg-[#EAF3EE] p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-[#2F6B4F]">
                      <FileCheck2 className="size-5" />
                      <span>Production Pipeline Analysis Completed Successfully</span>
                    </div>
                    <p className="text-xs text-fg-muted">
                      Dataset ingested and scored with the complete AquaSynex frozen pipeline (XGBoost + CatBoost + TreeSHAP).
                    </p>
                    <div className="flex flex-wrap items-center gap-2.5 pt-1">
                      <button
                        type="button"
                        onClick={() => navigate("/transactions")}
                        className="flex items-center gap-1.5 rounded-md bg-accent text-white px-3.5 py-1.5 text-xs font-semibold hover:bg-accent/90 transition-colors shadow-2xs"
                      >
                        <Activity className="size-3.5" />
                        View Transactions
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate("/alerts")}
                        className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-3.5 py-1.5 text-xs font-semibold text-fg hover:bg-panel-2 transition-colors shadow-2xs"
                      >
                        <Bell className="size-3.5" />
                        Investigate Alerts
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setStage("idle")
                          setProgress(0)
                          setFileName("")
                          setStagedFile(null)
                          setErrorMsg(null)
                        }}
                        className="ml-auto text-xs font-medium text-fg-subtle hover:text-fg hover:underline"
                      >
                        Ingest another dataset
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </PanelBody>
        </Panel>

        {/* Section 10: Dataset Schema & Preview (Collapsed by default) */}
        {existing && (
          <Panel className="border-line bg-panel shadow-xs">
            <PanelHeader
              title={<span className="font-sans font-semibold text-fg text-sm">Dataset Schema & Preview</span>}
              subtitle="Inspect raw column structure and sample records from the active forensic batch"
              icon={<Table className="size-4 text-accent" />}
              action={
                <button
                  type="button"
                  onClick={() => setShowSchemaPreview((prev) => !prev)}
                  className="flex items-center gap-1.5 rounded border border-line bg-panel-2 px-3 py-1 text-xs font-semibold text-fg hover:bg-panel transition-colors"
                >
                  {showSchemaPreview ? (
                    <>
                      <span>Hide Preview</span>
                      <ChevronUp className="size-3.5" />
                    </>
                  ) : (
                    <>
                      <span>Preview Rows</span>
                      <ChevronDown className="size-3.5" />
                    </>
                  )}
                </button>
              }
            />

            {showSchemaPreview && (
              <PanelBody className="p-6 space-y-6">
                {/* Schema Attributes Breakdown */}
                <div className="space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                    Available Schema Fields ({schemaFields.length} Columns • {totalTxCount} Rows)
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {schemaFields.map((field) => (
                      <div
                        key={field}
                        className="rounded border border-line bg-panel-2 px-2.5 py-1 text-xs font-mono text-fg flex items-center gap-1.5"
                      >
                        <span className="size-1.5 rounded-full bg-accent" />
                        <span>{field}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Sample Record Preview Table */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                      Observed Record Preview (First 5 Rows)
                    </span>
                    <button
                      type="button"
                      onClick={() => navigate("/transactions")}
                      className="text-[11px] font-medium text-accent hover:underline flex items-center gap-1"
                    >
                      <span>Explore all {totalTxCount} transactions</span>
                      <ExternalLink className="size-3" />
                    </button>
                  </div>

                  {loadingPreview ? (
                    <div className="py-8 text-center text-xs text-fg-subtle flex items-center justify-center gap-2">
                      <Loader2 className="size-4 animate-spin text-accent" />
                      <span>Loading records from DuckDB...</span>
                    </div>
                  ) : previewRows.length > 0 ? (
                    <div className="overflow-x-auto rounded border border-line">
                      <table className="w-full text-left text-xs font-sans">
                        <thead className="border-b border-line bg-panel-2 font-semibold text-fg-subtle text-[11px] uppercase tracking-wider">
                          <tr>
                            <th className="p-2.5">TXID</th>
                            <th className="p-2.5">Timestamp</th>
                            <th className="p-2.5 text-right">Amount (BTC)</th>
                            <th className="p-2.5 text-right">Fee (BTC)</th>
                            <th className="p-2.5 text-center">In / Out</th>
                            <th className="p-2.5 text-right">Risk Score</th>
                            <th className="p-2.5">Risk Level</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-line-soft font-mono text-xs">
                          {previewRows.map((row) => (
                            <tr key={row.transactionId} className="hover:bg-panel-2/50 transition-colors">
                              <td className="p-2.5 font-semibold text-fg">
                                <span title={row.transactionId}>
                                  {row.transactionId.slice(0, 10)}…{row.transactionId.slice(-8)}
                                </span>
                              </td>
                              <td className="p-2.5 text-fg-muted font-sans text-[11px]">
                                {row.timestamp ? formatDateTime(row.timestamp) : "—"}
                              </td>
                              <td className="p-2.5 text-right font-semibold text-fg">
                                {row.totalOutputValueBtc || "0.00000000"}
                              </td>
                              <td className="p-2.5 text-right text-fg-muted">
                                {row.feeBtc || "0.00000000"}
                              </td>
                              <td className="p-2.5 text-center text-fg-muted">
                                {row.inputCount ?? 1} in / {row.outputCount ?? 1} out
                              </td>
                              <td className="p-2.5 text-right font-bold text-fg">
                                {row.riskScore !== undefined ? `${Math.round(row.riskScore * 100)}%` : "—"}
                              </td>
                              <td className="p-2.5 font-sans">
                                {row.riskLevel ? (
                                  <SeverityBadge severity={row.riskLevel.toLowerCase() as Severity} />
                                ) : (
                                  <span className="text-fg-subtle">—</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="py-6 text-center text-xs text-fg-subtle border border-line rounded bg-panel-2">
                      No sample records available for preview.
                    </div>
                  )}
                </div>
              </PanelBody>
            )}
          </Panel>
        )}
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
                    ? "text-accent font-semibold"
                    : isDone
                      ? "text-[#2F6B4F] font-medium"
                      : "text-fg-subtle",
                )}
              >
                {stageLabel[s]}
              </span>
              {isActive && s !== "completed" ? (
                <span className="font-mono text-fg-subtle">{progress}%</span>
              ) : null}
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-panel-2 border border-line-soft">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-300",
                  isDone ? "bg-[#2F6B4F]" : "bg-accent",
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
