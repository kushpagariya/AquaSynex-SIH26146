import { useEffect, useState, useTransition } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  ArrowLeftRight,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  Search,
  SlidersHorizontal,
  ExternalLink,
  ShieldAlert,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import {
  getTransactionsDetailed,
  type FilteredTransactionsResponse,
} from "@/data/service"
import { BEHAVIOR_TYPOLOGIES, type BehaviorTypology, type Severity } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber, cn } from "@/lib/utils"

const severities: (Severity | "all")[] = ["all", "critical", "high", "medium", "low"]
const sortOptions = [
  { value: "timestamp:desc", label: "Newest First" },
  { value: "timestamp:asc", label: "Oldest First" },
  { value: "riskScore:desc", label: "Highest Risk" },
  { value: "riskScore:asc", label: "Lowest Risk" },
  { value: "amount:desc", label: "Highest Value" },
  { value: "amount:asc", label: "Lowest Value" },
]

export function TransactionsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const initialBehavior = searchParams.get("behavior") || "all"
  const initialSeverity = (searchParams.get("severity") as Severity) || "all"
  const initialSearch = searchParams.get("txid") || ""

  const [data, setData] = useState<FilteredTransactionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [, startTransition] = useTransition()

  // Filter States
  const [searchTxid, setSearchTxid] = useState(initialSearch)
  const [selectedSeverity, setSelectedSeverity] = useState<Severity | "all">(initialSeverity)
  const [selectedBehavior, setSelectedBehavior] = useState<string>(initialBehavior)
  const [minRisk, setMinRisk] = useState(0)
  const [maxRisk, setMaxRisk] = useState(100)
  const [sortKey, setSortKey] = useState("timestamp:desc")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [countryFilter, setCountryFilter] = useState("all")
  const [asnFilter, setAsnFilter] = useState("all")

  function loadTransactions() {
    setLoading(true)
    setErrorMsg(null)

    const [sortBy, sortDir] = sortKey.split(":") as [string, "asc" | "desc"]

    getTransactionsDetailed({
      page,
      pageSize,
      sortBy,
      sortDir,
      riskLevel: selectedSeverity === "all" ? undefined : selectedSeverity,
      minRiskScore: minRisk > 0 ? minRisk : undefined,
      maxRiskScore: maxRisk < 100 ? maxRisk : undefined,
      behavior: selectedBehavior === "all" ? undefined : selectedBehavior,
      searchTxid: searchTxid.trim() || undefined,
      country: countryFilter === "all" ? undefined : countryFilter,
      asn: asnFilter === "all" ? undefined : asnFilter,
    })
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load transactions")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadTransactions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortKey, selectedSeverity, selectedBehavior, minRisk, maxRisk, countryFilter, asnFilter])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    loadTransactions()
  }

  function handleResetFilters() {
    setSearchTxid("")
    setSelectedSeverity("all")
    setSelectedBehavior("all")
    setMinRisk(0)
    setMaxRisk(100)
    setCountryFilter("all")
    setAsnFilter("all")
    setPage(1)
    setSearchParams({})
  }

  // Extract distinct observed countries and ASNs from current result set
  const availableCountries = Array.from(
    new Set((data?.transactions || []).map((t) => t.network.countryCode).filter((c) => c && c !== "XX")),
  )
  const availableAsns = Array.from(
    new Set((data?.transactions || []).map((t) => t.network.asn).filter((a) => a && a !== "—")),
  )

  return (
    <AppLayout title="Transactions">
      <div className="space-y-5">
        {/* Top Control Bar */}
        <Panel>
          <PanelHeader
            title="Transaction Search & Criteria"
            subtitle="Search by hash, inspect behavioral typology, or filter by network broadcast"
            icon={<SlidersHorizontal className="size-4" />}
            action={
              <button
                type="button"
                onClick={loadTransactions}
                className="flex items-center gap-1.5 rounded border border-line bg-panel-2 px-2.5 py-1 text-xs text-fg-muted hover:text-accent"
              >
                <RefreshCw className="size-3.5" />
                Refresh
              </button>
            }
          />
          <div className="space-y-4 p-4">
            {/* Search Input Bar */}
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 size-4 text-fg-subtle" />
                <input
                  type="text"
                  value={searchTxid}
                  onChange={(e) => setSearchTxid(e.target.value)}
                  placeholder="Search full or partial TXID hash (e.g. a587d8...)"
                  className="w-full rounded-md border border-line bg-panel-2 py-2 pl-9 pr-4 text-xs font-mono-id text-fg placeholder:text-fg-subtle focus:border-accent focus:outline-none"
                />
              </div>
              <button
                type="submit"
                className="rounded-md border border-accent/40 bg-accent-soft px-4 py-2 text-xs font-medium text-accent hover:bg-accent/10"
              >
                Search
              </button>
              {(searchTxid || selectedSeverity !== "all" || selectedBehavior !== "all" || minRisk > 0 || countryFilter !== "all" || asnFilter !== "all") ? (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="rounded-md border border-line bg-panel-2 px-3 py-2 text-xs text-fg-muted hover:text-fg"
                >
                  Clear Filters
                </button>
              ) : null}
            </form>

            {/* Filter Rows */}
            <div className="grid grid-cols-1 gap-4 border-t border-line-soft pt-3 md:grid-cols-2 lg:grid-cols-4">
              {/* Severity Chips */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                  Severity Level
                </label>
                <div className="flex flex-wrap gap-1">
                  {severities.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => {
                        setSelectedSeverity(s)
                        setPage(1)
                      }}
                      className={cn(
                        "rounded border px-2 py-1 text-xs font-medium capitalize transition-colors",
                        selectedSeverity === s
                          ? "border-accent/40 bg-accent-soft text-accent"
                          : "border-line bg-panel-2 text-fg-muted hover:text-fg",
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Behavior Typology */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                  Behavior Typology
                </label>
                <select
                  value={selectedBehavior}
                  onChange={(e) => {
                    setSelectedBehavior(e.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded border border-line bg-panel-2 px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none"
                >
                  <option value="all">All Typologies (11 scenarios)</option>
                  {BEHAVIOR_TYPOLOGIES.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>

              {/* Observed Network Country */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                  Observed Country
                </label>
                <select
                  value={countryFilter}
                  onChange={(e) => {
                    setCountryFilter(e.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded border border-line bg-panel-2 px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none"
                >
                  <option value="all">All Countries</option>
                  {availableCountries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sorting & Risk Slider */}
              <div>
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                  Sort Order
                </label>
                <select
                  value={sortKey}
                  onChange={(e) => setSortKey(e.target.value)}
                  className="w-full rounded border border-line bg-panel-2 px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none"
                >
                  {sortOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Risk Range Slider */}
            <div className="flex flex-wrap items-center gap-4 border-t border-line-soft pt-3">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                ML Risk Range: {minRisk} — {maxRisk}
              </span>
              <input
                type="range"
                min={0}
                max={100}
                value={minRisk}
                onChange={(e) => setMinRisk(Number(e.target.value))}
                className="h-1.5 w-44 cursor-pointer appearance-none rounded-full bg-panel-2 accent-accent"
                aria-label="Minimum risk filter"
              />
              <span className="text-xs text-fg-subtle">Min: {minRisk}</span>
            </div>
          </div>
        </Panel>

        {/* Transactions Table Section */}
        <Panel>
          <PanelHeader
            title="Transactions Register"
            subtitle={
              data
                ? `Showing ${data.transactions.length} of ${formatNumber(data.totalItems)} transactions (Page ${data.page} of ${data.totalPages})`
                : "Querying canonical transactions"
            }
            icon={<ArrowLeftRight className="size-4" />}
            action={
              <div className="flex items-center gap-2 text-xs">
                <span className="text-fg-subtle">Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setPage(1)
                  }}
                  className="rounded border border-line bg-panel-2 px-2 py-1 text-xs text-fg focus:border-accent"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            }
          />

          {errorMsg ? (
            <ErrorState title="Failed to load transactions" description={errorMsg} />
          ) : loading ? (
            <LoadingState label="Fetching live transaction telemetry" />
          ) : !data || !data.transactions.length ? (
            <EmptyState
              title="No transactions match the selected filters"
              description="Try clearing search query, widening the risk score range, or selecting all typologies."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-wider text-fg-subtle">
                    <th className="px-4 py-2.5 font-medium">TXID</th>
                    <th className="px-4 py-2.5 font-medium">Timestamp</th>
                    <th className="px-4 py-2.5 font-medium">Amount (BTC)</th>
                    <th className="px-4 py-2.5 font-medium">Fee</th>
                    <th className="px-4 py-2.5 font-medium">Behavior Typology</th>
                    <th className="px-4 py-2.5 font-medium">Network Telemetry</th>
                    <th className="px-4 py-2.5 font-medium">Inferred Cluster</th>
                    <th className="px-4 py-2.5 font-medium">ML Risk</th>
                    <th className="px-4 py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.transactions.map((t) => (
                    <tr
                      key={t.txid}
                      onClick={() => navigate(`/investigation/${t.txid}?entityType=transaction`)}
                      className="group cursor-pointer border-b border-line-soft transition-colors last:border-0 hover:bg-panel-2"
                    >
                      <td className="px-4 py-3">
                        <MonoId value={t.txid} head={8} tail={6} copyable={false} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs text-fg-subtle">
                        {formatDateTime(t.timestamp)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono-id font-medium tabular-nums text-fg">
                        {formatBtc(t.amount)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs tabular-nums text-fg-subtle">
                        {t.fee.toFixed(5)} BTC
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center rounded border border-line bg-panel-2 px-2 py-0.5 font-mono-id text-[11px] text-fg-muted">
                          {t.behaviorType || "normal"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-fg-muted">
                        <span className="font-mono-id text-fg">
                          {t.network.countryCode !== "XX" ? t.network.countryCode : "—"}
                        </span>
                        {t.network.asn !== "—" ? (
                          <span className="ml-1.5 text-fg-subtle">AS{t.network.asn}</span>
                        ) : null}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono-id text-xs text-fg-subtle">
                        {t.clusterId ? (
                          <span className="text-accent">{t.clusterId}</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {t.severity ? (
                          <div className="flex items-center gap-2">
                            <span
                              className="font-mono-id text-xs font-semibold tabular-nums"
                              style={{ color: severityColorVar(t.severity) }}
                            >
                              {t.riskScore ?? "—"}
                            </span>
                            <SeverityBadge severity={t.severity} />
                          </div>
                        ) : (
                          <span className="text-xs text-fg-subtle">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/investigation/${t.txid}?entityType=transaction`)
                          }}
                          className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                        >
                          Investigate
                          <ExternalLink className="size-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {data && data.totalPages > 1 ? (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-xs">
              <span className="text-fg-subtle">
                Showing Page {data.page} of {data.totalPages} ({data.totalItems} total transactions)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={data.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="flex items-center gap-1 rounded border border-line bg-panel-2 px-2.5 py-1 text-fg-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="size-3.5" />
                  Previous
                </button>
                <span className="px-2 font-mono-id text-fg">{data.page}</span>
                <button
                  type="button"
                  disabled={data.page >= data.totalPages}
                  onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
                  className="flex items-center gap-1 rounded border border-line bg-panel-2 px-2.5 py-1 text-fg-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                  <ChevronRight className="size-3.5" />
                </button>
              </div>
            </div>
          ) : null}
        </Panel>
      </div>
    </AppLayout>
  )
}
