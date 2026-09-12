import { useEffect, useRef, useState } from "react"
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
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { getDatasetInfo } from "@/data/service"
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
  const [existing, setExisting] = useState<DatasetInfo | null>(null)
  const [stage, setStage] = useState<DatasetStage>("idle")
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState<string>("")
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getDatasetInfo().then(setExisting)
  }, [])

  function simulateIngest(name: string) {
    setFileName(name)
    setStage("uploading")
    setProgress(0)

    let pct = 0
    const upload = setInterval(() => {
      pct += 8
      setProgress(Math.min(pct, 100))
      if (pct >= 100) {
        clearInterval(upload)
        setStage("processing")
        setProgress(0)
        let ppct = 0
        const process = setInterval(() => {
          ppct += 5
          setProgress(Math.min(ppct, 100))
          if (ppct >= 100) {
            clearInterval(process)
            setStage("completed")
          }
        }, 120)
      }
    }, 90)
  }

  function onFiles(files: FileList | null) {
    if (files && files.length) simulateIngest(files[0].name)
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
                    accept=".csv,.json"
                    className="hidden"
                    onChange={(e) => onFiles(e.target.files)}
                  />
                </div>
              ) : (
                <div className="space-y-5 py-2">
                  <div className="flex items-center gap-3">
                    <span className="grid size-10 place-items-center rounded-md border border-line bg-panel-2 text-accent">
                      {stage === "completed" ? (
                        <FileCheck2 className="size-5" />
                      ) : (
                        <Loader2 className="size-5 animate-spin" />
                      )}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-mono-id text-sm text-fg">
                        {fileName}
                      </p>
                      <p className="text-xs text-fg-subtle">
                        {stageLabel[stage]}
                        {stage !== "completed" ? ` — ${progress}%` : ""}
                      </p>
                    </div>
                  </div>

                  <StageTracker stage={stage} progress={progress} />

                  {stage === "completed" ? (
                    <button
                      type="button"
                      onClick={() => {
                        setStage("idle")
                        setProgress(0)
                        setFileName("")
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
                        icon={Activity2}
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
                        value="5h"
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

function Activity2({ className }: { className?: string }) {
  return <Database className={className} />
}
