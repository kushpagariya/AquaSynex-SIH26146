import { useEffect, useState, useTransition } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import {
  ArrowLeftRight,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  Search,
  ExternalLink,
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
import { BEHAVIOR_TYPOLOGIES, type Severity } from "@/data/types"
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

  const availableCountries = Array.from(
    new Set((data?.transactions || []).map((t) => t.network.countryCode).filter((c) => c && c !== "XX")),
  )

  return (
    <AppLayout title="Transactions">
      <div className="space-y-6">
        {/* Compact Institutional Filter Toolbar */}
        <Panel>
          <PanelHeader
            title="Transactions Query & Filter"
            subtitle="Search by cryptographic hash or filter by behavioral typology and observed metadata"
            icon={<Filter className="size-4" />}
            action={
              <button
                type="button"
                onClick={loadTransactions}
                className="flex items-center gap-1.5 rounded border border-line bg-panel px-2.5 py-1 text-xs font-medium text-fg-muted hover:text-accent hover:border-gray-300 transition-colors font-sans"
              >
                <RefreshCw className="size-3.5" />
                Refresh
              </button>
            }
          />
          <div className="space-y-4 p-5">
            {/* Search Input Bar */}
            <form onSubmit={handleSearchSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 size-4 text-fg-subtle" />
                <input
                  type="text"
                  value={searchTxid}
                  onChange={(e) => setSearchTxid(e.target.value)}
                  placeholder="Search TXID hash (e.g. 8315167db4...)"
                  className="w-full rounded border border-line bg-panel-2 py-2 pl-9 pr-4 text-xs font-mono text-fg placeholder:text-fg-subtle placeholder:font-sans focus:border-accent focus:bg-panel focus:outline-none transition-colors"
                />
              </div>
              <button
                type="submit"
                className="rounded border border-accent bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent/90 transition-colors font-sans"
              >
                Search
              </button>
              {(searchTxid || selectedSeverity !== "all" || selectedBehavior !== "all" || minRisk > 0 || countryFilter !== "all" || asnFilter !== "all") ? (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="rounded border border-line bg-panel px-3 py-2 text-xs font-medium text-fg-muted hover:text-fg hover:border-gray-300 font-sans"
                >
                  Reset
                </button>
              ) : null}
            </form>

            {/* Compact Filter Controls Grid */}
            <div className="grid grid-cols-1 gap-4 border-t border-line-soft pt-4 sm:grid-cols-2 lg:grid-cols-4 text-xs font-sans">
              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-fg-muted">
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
                          ? "border-accent bg-accent-soft text-accent font-semibold"
                          : "border-line bg-panel text-fg-muted hover:text-fg hover:border-gray-300",
                      )}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-fg-muted">
                  Behavior Typology
                </label>
                <select
                  value={selectedBehavior}
                  onChange={(e) => {
                    setSelectedBehavior(e.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded border border-line bg-panel px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none font-sans"
                >
                  <option value="all">All Typologies (11 scenarios)</option>
                  {BEHAVIOR_TYPOLOGIES.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-fg-muted">
                  Observed Country
                </label>
                <select
                  value={countryFilter}
                  onChange={(e) => {
                    setCountryFilter(e.target.value)
                    setPage(1)
                  }}
                  className="w-full rounded border border-line bg-panel px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none font-sans"
                >
                  <option value="all">All Countries</option>
                  {availableCountries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-fg-muted">
                  Sort Order
                </label>
                <select
                  value={sortKey}
                  onChange={(e) => setSortKey(e.target.value)}
                  className="w-full rounded border border-line bg-panel px-2.5 py-1.5 text-xs text-fg focus:border-accent focus:outline-none font-sans"
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
            <div className="flex flex-wrap items-center gap-3 border-t border-line-soft pt-3 text-xs">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted font-sans">
                Minimum ML Risk Score: {minRisk}
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
            </div>
          </div>
        </Panel>

        {/* Transactions Ledger Register */}
        <Panel>
          <PanelHeader
            title="Transactions Ledger"
            subtitle={
              data
                ? `Displaying ${data.transactions.length} of ${formatNumber(data.totalItems)} records (Page ${data.page} of ${data.totalPages})`
                : "Querying transaction store"
            }
            icon={<ArrowLeftRight className="size-4" />}
            action={
              <div className="flex items-center gap-2 text-xs font-sans">
                <span className="text-fg-subtle">Rows:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setPage(1)
                  }}
                  className="rounded border border-line bg-panel px-2 py-1 text-xs text-fg focus:border-accent"
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
            <LoadingState label="Fetching transaction telemetry" />
          ) : !data || !data.transactions.length ? (
            <EmptyState
              title="No transactions match the selected filters"
              description="Try clearing search query, widening the risk score range, or selecting all typologies."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left font-sans">
                <thead>
                  <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                    <th className="px-5 py-3">TXID</th>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Behavior</th>
                    <th className="px-4 py-3">Risk</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft text-xs">
                  {data.transactions.map((t) => (
                    <tr
                      key={t.txid}
                      onClick={() => navigate(`/investigation/${t.txid}?entityType=transaction`)}
                      className="group cursor-pointer transition-colors hover:bg-accent-soft/30"
                    >
                      <td className="px-5 py-3.5">
                        <MonoId value={t.txid} head={8} tail={6} copyable={false} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 font-mono text-[11px] text-fg-subtle">
                        {formatDateTime(t.timestamp)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 font-sans font-semibold tabular-nums text-fg">
                        {formatBtc(t.amount)}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center rounded border border-line bg-panel-2 px-2 py-0.5 text-[11px] font-medium text-fg">
                          {t.behaviorType || "normal"}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 font-mono font-bold text-xs tabular-nums">
                        {t.severity ? (
                          <span className="inline-flex items-center gap-1.5" style={{ color: severityColorVar(t.severity) }}>
                            <span className="size-1.5 rounded-full" style={{ backgroundColor: severityColorVar(t.severity) }} />
                            <span>{t.riskScore ?? "—"}</span>
                            <span className="text-[10px] uppercase font-sans font-medium text-fg-subtle">
                              ({t.severity})
                            </span>
                          </span>
                        ) : (
                          <span className="text-fg-subtle font-normal">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent opacity-75 group-hover:opacity-100 transition-opacity">
                          Investigate <ExternalLink className="size-3" />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Institutional Pagination Footer */}
          {data && data.totalPages > 1 ? (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 text-xs font-sans">
              <span className="text-fg-muted">
                Page <span className="font-semibold text-fg">{data.page}</span> of {data.totalPages} ({formatNumber(data.totalItems)} total items)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={data.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="flex items-center gap-1 rounded border border-line bg-panel px-2.5 py-1 text-fg-muted hover:text-fg hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="size-3.5" />
                  Previous
                </button>
                <span className="px-2 font-mono text-fg font-medium">{data.page}</span>
                <button
                  type="button"
                  disabled={data.page >= data.totalPages}
                  onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
                  className="flex items-center gap-1 rounded border border-line bg-panel px-2.5 py-1 text-fg-muted hover:text-fg hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-40"
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
