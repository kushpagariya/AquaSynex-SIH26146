import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Globe2,
  Server,
  Radio,
  ShieldAlert,
  ExternalLink,
  Info,
  ChevronRight,
  Network,
  RotateCcw,
  ArrowRight,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getNetworkIntelligence } from "@/data/service"
import type { NetworkIntelligenceData } from "@/data/types"
import { formatBtc, formatNumber, cn } from "@/lib/utils"

export function NetworkPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<NetworkIntelligenceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Progressive disclosure drilldown: Country -> ASN -> IP -> Transaction -> Investigation
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null)
  const [selectedAsn, setSelectedAsn] = useState<string | null>(null)
  const [selectedIp, setSelectedIp] = useState<string | null>(null)
  const [showAllIps, setShowAllIps] = useState(false)

  function loadNetworkData() {
    setLoading(true)
    setErrorMsg(null)
    getNetworkIntelligence()
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err) => {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load network intelligence")
        setLoading(false)
      })
  }

  useEffect(() => {
    loadNetworkData()
  }, [])

  function resetAll() {
    setSelectedCountry(null)
    setSelectedAsn(null)
    setSelectedIp(null)
    setShowAllIps(false)
  }

  // Filtered views based on progressive disclosure
  const filteredAsns = (data?.asns || []).filter(
    (a) => !selectedCountry || a.label.includes(`(${selectedCountry})`),
  )

  const isIpDisclosed = Boolean(selectedCountry || selectedAsn || showAllIps)

  const filteredIps = (data?.topIps || []).filter((ip) => {
    if (selectedCountry && ip.country !== selectedCountry) return false
    if (selectedAsn && ip.asn !== selectedAsn) return false
    return true
  })

  const filteredSuspiciousEvents = (data?.suspiciousEvents || []).filter((e) => {
    if (selectedCountry && e.country !== selectedCountry) return false
    if (selectedAsn && e.asn !== selectedAsn && e.asnOrg !== selectedAsn) return false
    if (selectedIp && e.ip !== selectedIp) return false
    return true
  })

  return (
    <AppLayout title="Network Intelligence">
      <div className="space-y-6 font-sans">
        {/* Subtle Institutional Context Banner */}
        <div className="rounded border border-line bg-panel p-3.5 shadow-sm text-xs">
          <div className="flex items-start gap-2.5">
            <Info className="size-4 shrink-0 text-[#173B63] mt-0.5" />
            <p className="text-fg-muted leading-relaxed">
              <strong className="font-semibold text-fg">Observed P2P Broadcast Telemetry:</strong> Peer propagation vectors recorded at transaction announcement.
              Geographic and routing identities are contextual; elevated risk is driven exclusively by supervised behavioral ML features.
            </p>
          </div>
        </div>

        {/* Progressive Drill-down Navigation Path Bar */}
        <div className="rounded border border-line bg-panel px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-fg-subtle">
                Investigation Path:
              </span>

              {/* Step 1: Country */}
              <button
                type="button"
                onClick={() => {
                  setSelectedCountry(null)
                  setSelectedAsn(null)
                  setSelectedIp(null)
                }}
                className={cn(
                  "px-2 py-1 rounded text-xs transition-colors font-medium",
                  !selectedCountry
                    ? "bg-accent-soft text-accent font-semibold"
                    : "text-fg-muted hover:text-fg hover:bg-panel-2",
                )}
              >
                1. Country: {selectedCountry || "All Jurisdictions"}
              </button>

              <ChevronRight className="size-3.5 text-fg-subtle" />

              {/* Step 2: ASN */}
              <button
                type="button"
                onClick={() => {
                  setSelectedAsn(null)
                  setSelectedIp(null)
                }}
                disabled={!selectedCountry && !selectedAsn}
                className={cn(
                  "px-2 py-1 rounded text-xs transition-colors font-medium disabled:opacity-40",
                  selectedAsn
                    ? "bg-accent-soft text-accent font-semibold"
                    : "text-fg-muted hover:text-fg hover:bg-panel-2",
                )}
              >
                2. ASN: {selectedAsn || (selectedCountry ? "Select ASN" : "All ASNs")}
              </button>

              <ChevronRight className="size-3.5 text-fg-subtle" />

              {/* Step 3: IP */}
              <button
                type="button"
                onClick={() => setSelectedIp(null)}
                disabled={!isIpDisclosed && !selectedIp}
                className={cn(
                  "px-2 py-1 rounded text-xs transition-colors font-mono font-medium disabled:opacity-40",
                  selectedIp
                    ? "bg-accent-soft text-accent font-semibold"
                    : "text-fg-muted hover:text-fg hover:bg-panel-2",
                )}
              >
                3. IP: {selectedIp || (isIpDisclosed ? "Select IP Node" : "All Nodes")}
              </button>

              <ChevronRight className="size-3.5 text-fg-subtle" />

              {/* Step 4: Transaction */}
              <span className="text-fg-subtle text-xs">
                4. Transaction Investigation
              </span>
            </div>

            {(selectedCountry || selectedAsn || selectedIp || showAllIps) && (
              <button
                type="button"
                onClick={resetAll}
                className="flex items-center gap-1 text-xs text-accent hover:text-accent-strong transition-colors font-medium ml-auto"
              >
                <RotateCcw className="size-3" />
                Reset Path
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <LoadingState label="Aggregating broadcast network telemetry" />
        ) : errorMsg ? (
          <ErrorState title="Failed to load telemetry" description={errorMsg} />
        ) : !data ? (
          <EmptyState title="No network telemetry found in active dataset" />
        ) : (
          <div className="space-y-6">
            {/* 4 Clean Typography Metric Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <div className="rounded border border-line bg-panel p-4 shadow-sm">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
                  Broadcasting Countries
                </span>
                <p className="mt-1.5 font-mono text-2xl font-bold text-fg tabular-nums">
                  {data.countries.length}
                </p>
                <p className="mt-0.5 text-xs text-fg-subtle">Observed jurisdictions</p>
              </div>

              <div className="rounded border border-line bg-panel p-4 shadow-sm">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
                  Autonomous Systems (ASNs)
                </span>
                <p className="mt-1.5 font-mono text-2xl font-bold text-fg tabular-nums">
                  {data.asns.length}
                </p>
                <p className="mt-0.5 text-xs text-fg-subtle">Routing networks & ISPs</p>
              </div>

              <div className="rounded border border-line bg-panel p-4 shadow-sm">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
                  Standard Port Ratio
                </span>
                <p className="mt-1.5 font-mono text-2xl font-bold text-[#2F6B4F] tabular-nums">
                  {Math.round(
                    (data.ports.standardPortCount /
                      (data.ports.standardPortCount + data.ports.nonStandardPortCount || 1)) *
                      100,
                  )}
                  %
                </p>
                <p className="mt-0.5 text-xs text-fg-subtle">Bitcoin P2P Port 8333</p>
              </div>

              <div className="rounded border border-line bg-panel p-4 shadow-sm">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-fg-muted">
                  Suspicious Events
                </span>
                <p className="mt-1.5 font-mono text-2xl font-bold text-[#A63D3D] tabular-nums">
                  {data.suspiciousEvents.length}
                </p>
                <p className="mt-0.5 text-xs text-fg-subtle">Flagged by behavioral ML</p>
              </div>
            </div>

            {/* STAGE 1: Country & ASN Routing */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Country Distribution */}
              <Panel>
                <PanelHeader
                  title="1. Jurisdictions (Countries)"
                  subtitle="Click a country to reveal its routing ASNs and broadcasting IP nodes"
                  icon={<Globe2 className="size-4" />}
                />
                <PanelBody className="space-y-2.5">
                  {data.countries.map((c) => {
                    const isSelected = selectedCountry === c.key
                    return (
                      <div
                        key={c.key}
                        onClick={() => {
                          setSelectedCountry(isSelected ? null : c.key)
                          setSelectedAsn(null)
                          setSelectedIp(null)
                          setShowAllIps(false)
                        }}
                        className={cn(
                          "cursor-pointer rounded border p-3 transition-colors",
                          isSelected
                            ? "border-accent bg-accent-soft/50"
                            : "border-line bg-panel hover:bg-panel-2",
                        )}
                      >
                        <div className="flex items-center justify-between text-xs font-medium">
                          <span className="font-semibold text-fg">
                            {c.label} <span className="font-normal text-fg-muted">({c.count} TXs)</span>
                          </span>
                          <span className="font-mono text-fg-muted font-medium">{formatBtc(c.volumeBtc)}</span>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded bg-panel-2 border border-line-soft">
                          <div
                            className="h-full rounded bg-[#173B63] transition-all"
                            style={{ width: `${Math.max(c.percentage, 4)}%` }}
                          />
                        </div>
                        <div className="mt-1.5 flex justify-between text-[11px] text-fg-subtle">
                          <span>{c.percentage}% network share</span>
                          {c.riskCount > 0 ? (
                            <span className="text-[#A63D3D] font-medium">
                              {c.riskCount} suspicious events
                            </span>
                          ) : (
                            <span>Standard traffic</span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </PanelBody>
              </Panel>

              {/* ASN Distribution */}
              <Panel>
                <PanelHeader
                  title="2. Autonomous Systems (ASNs)"
                  subtitle={
                    selectedCountry
                      ? `Routing networks active in ${selectedCountry}`
                      : "Click an ASN to isolate its member broadcasting nodes"
                  }
                  icon={<Server className="size-4" />}
                />
                <PanelBody className="space-y-2.5">
                  {filteredAsns.length === 0 ? (
                    <div className="py-12 text-center text-xs text-fg-subtle">
                      No ASNs recorded for country {selectedCountry}.
                    </div>
                  ) : (
                    filteredAsns.slice(0, 8).map((a) => {
                      const isSelected = selectedAsn === a.key
                      return (
                        <div
                          key={a.key}
                          onClick={() => {
                            setSelectedAsn(isSelected ? null : a.key)
                            setSelectedIp(null)
                            setShowAllIps(false)
                          }}
                          className={cn(
                            "cursor-pointer rounded border p-3 transition-colors",
                            isSelected
                              ? "border-accent bg-accent-soft/50"
                              : "border-line bg-panel hover:bg-panel-2",
                          )}
                        >
                          <div className="flex items-center justify-between text-xs font-medium">
                            <span className="font-mono text-fg font-semibold">{a.label}</span>
                            <span className="font-mono text-fg-muted">{a.count} TXs</span>
                          </div>
                          <div className="mt-2 h-1.5 overflow-hidden rounded bg-panel-2 border border-line-soft">
                            <div
                              className="h-full rounded bg-[#60758C] transition-all"
                              style={{ width: `${Math.max(a.percentage, 4)}%` }}
                            />
                          </div>
                          <div className="mt-1.5 flex justify-between text-[11px] text-fg-subtle">
                            <span>{formatBtc(a.volumeBtc)} volume</span>
                            <span>{a.percentage}% share</span>
                          </div>
                        </div>
                      )
                    })
                  )}
                </PanelBody>
              </Panel>
            </div>

            {/* STAGE 2: Progressive Disclosure of IP Nodes */}
            {!isIpDisclosed ? (
              <div className="rounded border border-dashed border-line bg-panel p-6 text-center">
                <div className="mx-auto grid size-10 place-items-center rounded bg-panel-2 text-fg-subtle mb-3">
                  <Network className="size-5 text-accent" />
                </div>
                <h3 className="text-sm font-semibold text-fg">
                  Stage 2: IP Node Disclosure
                </h3>
                <p className="mt-1 text-xs text-fg-muted max-w-md mx-auto">
                  Select any Jurisdiction (Country) or Autonomous System (ASN) above to inspect individual broadcasting IP nodes, or view all active nodes.
                </p>
                <div className="mt-4 flex justify-center">
                  <button
                    type="button"
                    onClick={() => setShowAllIps(true)}
                    className="flex items-center gap-1.5 rounded border border-line bg-panel-2 px-3.5 py-1.5 text-xs font-medium text-fg hover:border-gray-300 transition-colors"
                  >
                    View All {data.topIps.length} IP Nodes
                  </button>
                </div>
              </div>
            ) : (
              <Panel>
                <PanelHeader
                  title="3. Broadcasting IP Nodes"
                  subtitle={
                    selectedAsn
                      ? `IP nodes broadcasting via ${selectedAsn}`
                      : selectedCountry
                        ? `IP nodes broadcasting from ${selectedCountry}`
                        : "All observed broadcasting IP nodes"
                  }
                  icon={<Network className="size-4" />}
                  action={
                    <span className="text-xs text-fg-muted font-medium">
                      Showing {filteredIps.length} nodes
                    </span>
                  }
                />
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                        <th className="px-5 py-3 font-sans">IP Address</th>
                        <th className="px-4 py-3 font-sans">Country</th>
                        <th className="px-4 py-3 font-sans">ASN</th>
                        <th className="px-4 py-3 font-sans">Transactions</th>
                        <th className="px-4 py-3 font-sans">Volume (BTC)</th>
                        <th className="px-4 py-3 font-sans">Max Risk</th>
                        <th className="px-4 py-3 text-right font-sans">Drill Down</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line-soft">
                      {filteredIps.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="px-5 py-8 text-center text-xs text-fg-subtle">
                            No IP nodes match the current filter.
                          </td>
                        </tr>
                      ) : (
                        filteredIps.map((ip) => {
                          const isSelected = selectedIp === ip.ip
                          return (
                            <tr
                              key={ip.ip}
                              onClick={() => setSelectedIp(isSelected ? null : ip.ip)}
                              className={cn(
                                "cursor-pointer transition-colors",
                                isSelected
                                  ? "bg-accent-soft/50 border-l-2 border-l-accent"
                                  : "hover:bg-panel-2",
                              )}
                            >
                              <td className="px-5 py-3.5 font-mono text-xs font-semibold text-fg">
                                {ip.ip}
                              </td>
                              <td className="px-4 py-3.5 text-fg-muted">
                                {ip.country}
                              </td>
                              <td className="px-4 py-3.5 font-mono text-fg-subtle">
                                {ip.asn}
                              </td>
                              <td className="px-4 py-3.5 font-mono tabular-nums text-fg font-medium">
                                {ip.txCount}
                              </td>
                              <td className="px-4 py-3.5 font-semibold tabular-nums text-fg">
                                {formatBtc(ip.volumeBtc)}
                              </td>
                              <td className="px-4 py-3.5">
                                <span
                                  className="font-mono text-xs font-bold tabular-nums"
                                  style={{
                                    color: ip.maxRisk >= 65 ? "#A63D3D" : ip.maxRisk >= 35 ? "#A46A16" : "#2F6B4F",
                                  }}
                                >
                                  {ip.maxRisk} / 100
                                </span>
                              </td>
                              <td className="px-4 py-3.5 text-right">
                                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline">
                                  {isSelected ? "Isolating Transactions" : "Filter TXs"} <ArrowRight className="size-3" />
                                </span>
                              </td>
                            </tr>
                          )
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </Panel>
            )}

            {/* STAGE 3: Progressive Disclosure of Connected Transactions */}
            <Panel>
              <PanelHeader
                title="4. Associated Broadcast Transactions"
                subtitle={
                  selectedIp
                    ? `Transactions broadcast through node ${selectedIp}`
                    : selectedAsn
                      ? `Transactions broadcast through ASN ${selectedAsn}`
                      : selectedCountry
                        ? `Transactions broadcast from ${selectedCountry}`
                        : "Suspicious transactions with broadcast network telemetry"
                }
                icon={<ShieldAlert className="size-4" />}
                action={
                  <span className="rounded bg-[#FDF0F0] border border-[#F4BCBC] px-2.5 py-0.5 text-xs font-semibold text-[#A63D3D] font-mono">
                    {filteredSuspiciousEvents.length} Events
                  </span>
                }
              />
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-line bg-panel-2/60 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle select-none">
                      <th className="px-5 py-3 font-sans">Transaction</th>
                      <th className="px-4 py-3 font-sans">Broadcasting Node</th>
                      <th className="px-4 py-3 font-sans">ASN / Network</th>
                      <th className="px-4 py-3 font-sans">Country</th>
                      <th className="px-4 py-3 font-sans">Behavior</th>
                      <th className="px-4 py-3 font-sans">ML Risk</th>
                      <th className="px-4 py-3 text-right font-sans">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {filteredSuspiciousEvents.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-5 py-8 text-center text-xs text-fg-subtle">
                          No suspicious broadcast transactions match the current drilldown filter.
                        </td>
                      </tr>
                    ) : (
                      filteredSuspiciousEvents.map((e) => (
                        <tr
                          key={`${e.txid}-${e.ip}`}
                          onClick={() => navigate(`/investigation/${e.txid}?entityType=transaction`)}
                          className="cursor-pointer transition-colors hover:bg-panel-2"
                        >
                          <td className="px-5 py-3.5">
                            <MonoId value={e.txid} head={8} tail={6} copyable={false} />
                          </td>
                          <td className="px-4 py-3.5 font-mono text-xs text-fg font-medium">
                            {e.ip}:{e.port}
                          </td>
                          <td className="px-4 py-3.5 text-fg-muted truncate max-w-[150px]">
                            {e.asnOrg}
                          </td>
                          <td className="px-4 py-3.5 text-fg">
                            {e.country}
                          </td>
                          <td className="px-4 py-3.5">
                            <span className="rounded border border-line bg-panel-2 px-2 py-0.5 text-[11px] text-fg-muted">
                              {e.behaviorType || "anomalous"}
                            </span>
                          </td>
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-1.5">
                              <span
                                className="font-mono text-xs font-bold tabular-nums"
                                style={{ color: severityColorVar(e.severity) }}
                              >
                                {e.riskScore}
                              </span>
                              <SeverityBadge severity={e.severity} />
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline">
                              Investigate Case <ExternalLink className="size-3" />
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
