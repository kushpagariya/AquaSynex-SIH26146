import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import {
  Globe2,
  Server,
  Radio,
  Search,
  RotateCcw,
  ExternalLink,
  Info,
  MapPin,
  ShieldCheck,
  AlertCircle,
  Network,
  ArrowRight,
  Filter,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getNetworkMapData } from "@/data/service"
import type { NetworkMapPoint, NetworkMapResponse } from "@/api/types"
import { OfflineLeafletMap } from "@/components/network/offline-leaflet-map"
import { formatNumber, cn } from "@/lib/utils"

export function NetworkMapPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<NetworkMapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Filter states
  const [countryFilter, setCountryFilter] = useState("all")
  const [asnFilter, setAsnFilter] = useState("all")
  const [ipSearch, setIpSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | "mapped" | "unmapped">("all")

  // Selected Endpoint state
  const [selectedPoint, setSelectedPoint] = useState<NetworkMapPoint | null>(null)

  function loadData() {
    setLoading(true)
    setErrorMsg(null)
    getNetworkMapData()
      .then((res) => {
        setData(res)
        if (res && res.points.length > 0) {
          // Select first mapped point by default if available
          const firstMapped = res.points.find((p) => p.isMapped) || res.points[0]
          setSelectedPoint(firstMapped)
        }
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load network intelligence map data")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadData()
  }, [])

  // Derived filter options from actual data
  const availableCountries = useMemo(() => {
    if (!data) return []
    const set = new Set<string>()
    data.points.forEach((p) => {
      if (p.country) set.add(p.country)
    })
    return Array.from(set).sort()
  }, [data])

  const availableAsns = useMemo(() => {
    if (!data) return []
    const set = new Set<string>()
    data.points.forEach((p) => {
      if (p.asn) set.add(p.asn)
    })
    return Array.from(set).sort()
  }, [data])

  // Filtered points
  const filteredPoints = useMemo(() => {
    if (!data) return []
    const search = ipSearch.trim().toLowerCase()

    return data.points.filter((pt) => {
      if (countryFilter !== "all" && pt.country !== countryFilter) return false
      if (asnFilter !== "all" && pt.asn !== asnFilter) return false
      if (statusFilter === "mapped" && !pt.isMapped) return false
      if (statusFilter === "unmapped" && pt.isMapped) return false
      if (search) {
        const matchIp = pt.ip.toLowerCase().includes(search)
        const matchAsn = pt.asn?.toLowerCase().includes(search)
        const matchOrg = pt.asName?.toLowerCase().includes(search)
        const matchCountry = pt.country?.toLowerCase().includes(search)
        if (!matchIp && !matchAsn && !matchOrg && !matchCountry) return false
      }
      return true
    })
  }, [data, countryFilter, asnFilter, statusFilter, ipSearch])

  function resetFilters() {
    setCountryFilter("all")
    setAsnFilter("all")
    setIpSearch("")
    setStatusFilter("all")
  }

  if (loading) {
    return (
      <AppLayout title="Network Map">
        <LoadingState label="Loading and enriching network telemetry from local MMDB databases" />
      </AppLayout>
    )
  }

  if (errorMsg) {
    return (
      <AppLayout title="Network Map">
        <ErrorState
          title="Network Map Error"
          description={errorMsg}
        />
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={loadData}
            className="rounded border border-line bg-panel px-3 py-1.5 text-xs font-medium text-fg hover:bg-muted"
          >
            Retry
          </button>
        </div>
      </AppLayout>
    )
  }

  if (!data || data.points.length === 0) {
    return (
      <AppLayout title="Network Map">
        <EmptyState
          title="No Network Events Found"
          description="The active dataset does not contain observed P2P broadcast telemetry or IP network events."
          action={
            <button
              type="button"
              onClick={() => navigate("/dataset")}
              className="rounded bg-[#173B63] px-3.5 py-1.5 text-xs font-medium text-white hover:bg-[#122e4e] transition-colors"
            >
              Go to Dataset
            </button>
          }
        />
      </AppLayout>
    )
  }

  const metrics = data.metrics

  return (
    <AppLayout title="Network Map">
      <div className="space-y-5 font-sans">
        {/* Context Information Banner */}
        <div className="rounded border border-line bg-panel p-3 shadow-sm text-xs">
          <div className="flex items-start gap-2.5">
            <Info className="size-4 shrink-0 text-[#173B63] mt-0.5" />
            <div className="flex-1 text-fg-muted leading-relaxed">
              <strong className="font-semibold text-fg">Offline GeoIP & Routing Intelligence:</strong> Aggregated
              Bitcoin P2P broadcast propagation vectors enriched offline via MaxMind GeoLite2-City and IPinfo Lite MMDBs.
              No external APIs or remote tile servers are contacted at runtime.
            </div>
          </div>
        </div>

        {/* Summary Metrics Bar */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Observed IPs</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-fg">{formatNumber(metrics.totalIps)}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">Unique endpoints</p>
          </div>

          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Geolocated IPs</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-emerald-600">{formatNumber(metrics.mappedIps)}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">With coordinates</p>
          </div>

          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Unmapped IPs</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-amber-600">{formatNumber(metrics.unmappedIps)}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">Private / unresolvable</p>
          </div>

          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Countries</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-fg">{metrics.uniqueCountries}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">National jurisdictions</p>
          </div>

          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Autonomous Systems</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-fg">{metrics.uniqueAsns}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">Distinct BGP ASNs</p>
          </div>

          <div className="rounded-lg border border-line bg-panel p-3.5 shadow-sm">
            <p className="text-[11px] font-medium text-fg-muted">Total Network Events</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-[#173B63]">{formatNumber(metrics.totalEvents)}</p>
            <p className="text-[10px] text-fg-subtle mt-0.5">Broadcast signals</p>
          </div>
        </div>

        {/* Filters Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-panel p-3 shadow-sm text-xs">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1.5 text-fg-muted font-medium pr-1">
              <Filter className="size-3.5" />
              <span>Filters:</span>
            </div>

            {/* Country Dropdown */}
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="h-8 rounded border border-line bg-panel px-2.5 text-xs text-fg focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Countries ({availableCountries.length})</option>
              {availableCountries.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {/* ASN Dropdown */}
            <select
              value={asnFilter}
              onChange={(e) => setAsnFilter(e.target.value)}
              className="h-8 rounded border border-line bg-panel px-2.5 text-xs text-fg focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All ASNs ({availableAsns.length})</option>
              {availableAsns.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>

            {/* Mapping Status */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="h-8 rounded border border-line bg-panel px-2.5 text-xs text-fg focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Statuses</option>
              <option value="mapped">Mapped on Globe</option>
              <option value="unmapped">Unmapped Only</option>
            </select>

            {/* IP Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-fg-subtle" />
              <input
                type="text"
                placeholder="Search IP / ASN / Org..."
                value={ipSearch}
                onChange={(e) => setIpSearch(e.target.value)}
                className="h-8 w-44 rounded border border-line bg-panel pl-7 pr-2.5 text-xs text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-fg-muted font-mono">
              Showing {filteredPoints.length} of {data.points.length} endpoints
            </span>
            {(countryFilter !== "all" || asnFilter !== "all" || ipSearch || statusFilter !== "all") && (
              <button
                type="button"
                onClick={resetFilters}
                className="flex items-center gap-1 text-[11px] text-fg-muted hover:text-fg transition-colors"
              >
                <RotateCcw className="size-3" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Main Grid: Map & Selected Endpoint Detail Panel */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          {/* Left / Center 2 Cols: The Offline Map */}
          <div className="lg:col-span-2 space-y-4">
            <Panel className="overflow-hidden">
              <PanelHeader
                title="Geographic Node Distribution"
                subtitle="Local vector projection rendered via Leaflet"
                icon={<Globe2 className="size-4" />}
              />
              <div className="p-3">
                <OfflineLeafletMap
                  points={filteredPoints}
                  selectedIp={selectedPoint?.ip || null}
                  onSelectPoint={(pt) => setSelectedPoint(pt)}
                  className="h-[520px]"
                />
              </div>
            </Panel>
          </div>

          {/* Right 1 Col: Selected Endpoint Detail & Action Card */}
          <div className="space-y-4">
            <Panel>
              <PanelHeader
                title="Selected Endpoint"
                subtitle={selectedPoint ? selectedPoint.ip : "No endpoint selected"}
                icon={<Server className="size-4" />}
              />
              <PanelBody className="space-y-4 text-xs">
                {selectedPoint ? (
                  <>
                    <div className="flex items-center justify-between border-b border-line pb-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">IP Address</p>
                        <div className="mt-0.5 flex items-center gap-2">
                          <MonoId value={selectedPoint.ip} truncate={false} className="text-sm font-bold text-fg" />
                          {selectedPoint.isMapped ? (
                            <span className="inline-flex items-center rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-medium text-emerald-700 border border-emerald-200">
                              Geolocated
                            </span>
                          ) : (
                            <span className="inline-flex items-center rounded-full bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium text-amber-700 border border-amber-200">
                              Unmapped
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 border-b border-line pb-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Country</p>
                        <p className="mt-0.5 font-medium text-fg">{selectedPoint.country || "Unknown"}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Region / City</p>
                        <p className="mt-0.5 font-medium text-fg">
                          {selectedPoint.city || selectedPoint.region
                            ? `${selectedPoint.city || ""}${selectedPoint.city && selectedPoint.region ? ", " : ""}${selectedPoint.region || ""}`
                            : "Unavailable"}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2 border-b border-line pb-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Autonomous System</p>
                        <p className="mt-0.5 font-mono text-fg">{selectedPoint.asn || "Unspecified ASN"}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Organization / Domain</p>
                        <p className="mt-0.5 text-fg-muted truncate">
                          {selectedPoint.asName || "Private or Unspecified Network"}
                          {selectedPoint.asDomain ? ` (${selectedPoint.asDomain})` : ""}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 border-b border-line pb-3">
                      <div className="rounded bg-muted/40 p-2 border border-line/60">
                        <p className="text-[10px] text-fg-subtle uppercase">Network Events</p>
                        <p className="text-base font-bold text-fg mt-0.5">{selectedPoint.eventCount}</p>
                        <p className="text-[9px] text-fg-subtle mt-0.5">
                          Src: {selectedPoint.sourceEventCount} • Dst: {selectedPoint.destinationEventCount}
                        </p>
                      </div>
                      <div className="rounded bg-muted/40 p-2 border border-line/60">
                        <p className="text-[10px] text-fg-subtle uppercase">Transactions</p>
                        <p className="text-base font-bold text-fg mt-0.5">{selectedPoint.transactionCount}</p>
                        <p className="text-[9px] text-fg-subtle mt-0.5">Associated on-chain</p>
                      </div>
                    </div>

                    {selectedPoint.latitude !== null && selectedPoint.longitude !== null && (
                      <div className="border-b border-line pb-3 text-[11px] text-fg-muted font-mono flex items-center justify-between">
                        <span>Coordinates:</span>
                        <span>
                          {selectedPoint.latitude?.toFixed(4)}, {selectedPoint.longitude?.toFixed(4)}
                        </span>
                      </div>
                    )}

                    {/* Drill-down Actions */}
                    <div className="space-y-2 pt-1">
                      <button
                        type="button"
                        onClick={() => navigate(`/transactions?ip=${encodeURIComponent(selectedPoint.ip)}`)}
                        className="w-full flex items-center justify-center gap-1.5 rounded bg-[#173B63] hover:bg-[#122e4e] text-white py-2 px-3 text-xs font-semibold shadow-sm transition-colors"
                      >
                        <span>View Transactions</span>
                        <ArrowRight className="size-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate(`/investigation?ip=${encodeURIComponent(selectedPoint.ip)}`)}
                        className="w-full flex items-center justify-center gap-1.5 rounded border border-line bg-panel hover:bg-muted/50 text-fg py-2 px-3 text-xs font-medium transition-colors"
                      >
                        <ExternalLink className="size-3.5 text-fg-muted" />
                        <span>Open in Investigation</span>
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="py-8 text-center text-fg-subtle">
                    Click a node on the map to view its enriched intelligence.
                  </div>
                )}
              </PanelBody>
            </Panel>
          </div>
        </div>

        {/* Endpoints Table (Supports Viewing and Selecting all nodes including Unmapped) */}
        <Panel>
          <PanelHeader
            title="Network Endpoints Roster"
            subtitle="Full inventory of observed IPs, including unmapped or private nodes"
            icon={<Network className="size-4" />}
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-line bg-muted/30 font-medium text-fg-muted">
                  <th className="py-2.5 px-4">IP Address</th>
                  <th className="py-2.5 px-4">Country</th>
                  <th className="py-2.5 px-4">Autonomous System</th>
                  <th className="py-2.5 px-4 text-center">Events</th>
                  <th className="py-2.5 px-4 text-center">Txs</th>
                  <th className="py-2.5 px-4 text-center">Status</th>
                  <th className="py-2.5 px-4 text-right">Drill-Down</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredPoints.slice(0, 50).map((pt) => {
                  const isSelected = selectedPoint?.ip === pt.ip
                  return (
                    <tr
                      key={pt.ip}
                      onClick={() => setSelectedPoint(pt)}
                      className={cn(
                        "cursor-pointer transition-colors hover:bg-muted/40",
                        isSelected && "bg-primary/5 font-medium",
                      )}
                    >
                      <td className="py-2.5 px-4 font-mono font-semibold text-fg">
                        {pt.ip}
                      </td>
                      <td className="py-2.5 px-4 text-fg-muted">
                        {pt.country || "—"}
                      </td>
                      <td className="py-2.5 px-4 text-fg-muted truncate max-w-xs">
                        {pt.asn ? `${pt.asn} ${pt.asName ? `(${pt.asName})` : ""}` : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-center font-mono">
                        {pt.eventCount}
                      </td>
                      <td className="py-2.5 px-4 text-center font-mono">
                        {pt.transactionCount}
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        {pt.isMapped ? (
                          <span className="inline-block size-2 rounded-full bg-emerald-500" title="Geolocated" />
                        ) : (
                          <span className="inline-block size-2 rounded-full bg-amber-500" title="Unmapped" />
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/transactions?ip=${encodeURIComponent(pt.ip)}`)
                          }}
                          className="inline-flex items-center gap-1 text-[11px] font-medium text-[#173B63] hover:underline"
                        >
                          <span>Transactions</span>
                          <ArrowRight className="size-3" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {filteredPoints.length > 50 && (
              <div className="p-3 text-center text-xs text-fg-muted border-t border-line bg-muted/10">
                Showing top 50 of {filteredPoints.length} matching endpoints. Use filters above to narrow results.
              </div>
            )}
          </div>
        </Panel>
      </div>
    </AppLayout>
  )
}
