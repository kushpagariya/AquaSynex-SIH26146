import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Network,
  Globe2,
  Server,
  Radio,
  Clock,
  ShieldAlert,
  ExternalLink,
  Info,
  RefreshCw,
  Filter,
  ArrowRight,
  Activity,
} from "lucide-react"
import { AppLayout } from "@/components/layout/app-layout"
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel"
import { SeverityBadge, severityColorVar } from "@/components/ui/badges"
import { MonoId } from "@/components/ui/mono-id"
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/states"
import { getNetworkIntelligence } from "@/data/service"
import type { NetworkIntelligenceData, Severity } from "@/data/types"
import { formatBtc, formatDateTime, formatNumber, cn } from "@/lib/utils"

export function NetworkPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<NetworkIntelligenceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Interactive drilldown states: Country -> ASN -> IP
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null)
  const [selectedAsn, setSelectedAsn] = useState<string | null>(null)
  const [selectedIp, setSelectedIp] = useState<string | null>(null)

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

  // Filtered views based on drilldown
  const filteredAsns = (data?.asns || []).filter(
    (a) => !selectedCountry || a.label.includes(`(${selectedCountry})`),
  )

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
      <div className="space-y-6">
        {/* Data Honesty Notice */}
        <div className="rounded-lg border border-line bg-panel p-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded bg-accent-soft text-accent">
              <Info className="size-4" />
            </span>
            <div className="space-y-1">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-fg">
                Observed Network Telemetry Disclaimer
              </h3>
              <p className="text-xs leading-relaxed text-fg-muted">
                Network metrics represent observed broadcast peer telemetry recorded at transaction announcement time.
                <strong className="text-fg ml-1">
                  A country, ASN, or hosting provider is never marked suspicious solely due to its geographic or organizational identity.
                </strong>{" "}
                Elevated risk flags are produced exclusively by the machine learning model based on behavioral feature anomalies.
              </p>
            </div>
          </div>
        </div>

        {/* Drilldown Navigation Breadcrumbs */}
        {(selectedCountry || selectedAsn || selectedIp) && (
          <div className="flex items-center gap-2 rounded-md border border-accent/30 bg-accent-soft/40 px-3.5 py-2 text-xs">
            <span className="font-semibold text-accent uppercase tracking-wider">Drilldown Filter:</span>
            <button
              type="button"
              onClick={() => {
                setSelectedCountry(null)
                setSelectedAsn(null)
                setSelectedIp(null)
              }}
              className="text-fg-muted hover:text-fg underline"
            >
              All Telemetry
            </button>
            {selectedCountry ? (
              <>
                <ArrowRight className="size-3 text-fg-subtle" />
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAsn(null)
                    setSelectedIp(null)
                  }}
                  className="font-mono-id text-fg hover:underline font-semibold"
                >
                  Country: {selectedCountry}
                </button>
              </>
            ) : null}
            {selectedAsn ? (
              <>
                <ArrowRight className="size-3 text-fg-subtle" />
                <button
                  type="button"
                  onClick={() => setSelectedIp(null)}
                  className="font-mono-id text-fg hover:underline font-semibold"
                >
                  ASN: {selectedAsn}
                </button>
              </>
            ) : null}
            {selectedIp ? (
              <>
                <ArrowRight className="size-3 text-fg-subtle" />
                <span className="font-mono-id text-accent font-semibold">
                  IP: {selectedIp}
                </span>
              </>
            ) : null}
            <button
              type="button"
              onClick={() => {
                setSelectedCountry(null)
                setSelectedAsn(null)
                setSelectedIp(null)
              }}
              className="ml-auto text-[11px] text-accent hover:underline font-medium"
            >
              Clear Drilldown
            </button>
          </div>
        )}

        {loading ? (
          <LoadingState label="Aggregating network broadcast telemetry" />
        ) : errorMsg ? (
          <ErrorState title="Failed to load telemetry" description={errorMsg} />
        ) : !data ? (
          <EmptyState title="No network telemetry found in active dataset" />
        ) : (
          <div className="space-y-6">
            {/* Top Metric Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <div className="rounded-[var(--radius-panel)] border border-line bg-panel p-4">
                <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">
                  Broadcasting Countries
                </span>
                <p className="mt-2 font-mono-id text-2xl font-bold text-fg">
                  {data.countries.length}
                </p>
                <p className="mt-1 text-xs text-fg-subtle">Observed geographic origins</p>
              </div>

              <div className="rounded-[var(--radius-panel)] border border-line bg-panel p-4">
                <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">
                  Autonomous Systems (ASNs)
                </span>
                <p className="mt-2 font-mono-id text-2xl font-bold text-fg">
                  {data.asns.length}
                </p>
                <p className="mt-1 text-xs text-fg-subtle">Routing networks & ISPs</p>
              </div>

              <div className="rounded-[var(--radius-panel)] border border-line bg-panel p-4">
                <span className="text-xs font-medium uppercase tracking-wider text-fg-subtle">
                  P2P Port Conformance
                </span>
                <p className="mt-2 font-mono-id text-2xl font-bold text-fg">
                  {data.ports.standardPortCount} / {data.ports.standardPortCount + data.ports.nonStandardPortCount}
                </p>
                <p className="mt-1 text-xs text-fg-subtle">Standard Bitcoin Port (8333)</p>
              </div>

              <div className="rounded-[var(--radius-panel)] border border-line bg-panel p-4">
                <span className="text-xs font-medium uppercase tracking-wider text-risk-high">
                  Suspicious Network Events
                </span>
                <p className="mt-2 font-mono-id text-2xl font-bold text-risk-high">
                  {data.suspiciousEvents.length}
                </p>
                <p className="mt-1 text-xs text-fg-subtle">ML high/critical risk events</p>
              </div>
            </div>

            {/* Middle Grid: Country Distribution & ASN Distribution */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Country Distribution */}
              <Panel>
                <PanelHeader
                  title="Country Distribution"
                  subtitle="Click country to filter ASNs and broadcasting nodes"
                  icon={<Globe2 className="size-4" />}
                />
                <PanelBody className="space-y-3">
                  {data.countries.map((c) => {
                    const isSelected = selectedCountry === c.key
                    return (
                      <div
                        key={c.key}
                        onClick={() => {
                          setSelectedCountry(isSelected ? null : c.key)
                          setSelectedAsn(null)
                          setSelectedIp(null)
                        }}
                        className={cn(
                          "group cursor-pointer rounded border p-2.5 transition-colors",
                          isSelected
                            ? "border-accent bg-accent-soft/40"
                            : "border-line-soft bg-panel-2/50 hover:bg-panel-2",
                        )}
                      >
                        <div className="flex items-center justify-between text-xs font-medium">
                          <span className="font-mono-id text-fg">
                            {c.label} ({c.count} transactions)
                          </span>
                          <span className="font-mono-id text-fg-muted">{formatBtc(c.volumeBtc)}</span>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-panel">
                          <div
                            className="h-full rounded-full bg-accent transition-all"
                            style={{ width: `${Math.max(c.percentage, 4)}%` }}
                          />
                        </div>
                        <div className="mt-1.5 flex justify-between text-[11px] text-fg-subtle">
                          <span>{c.percentage}% of network share</span>
                          {c.riskCount > 0 ? (
                            <span className="text-risk-high font-medium">
                              {c.riskCount} suspicious events
                            </span>
                          ) : (
                            <span>Standard</span>
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
                  title="Autonomous System (ASN) Distribution"
                  subtitle="Click ASN to inspect specific broadcasting nodes"
                  icon={<Server className="size-4" />}
                />
                <PanelBody className="space-y-3">
                  {filteredAsns.length === 0 ? (
                    <p className="text-xs text-fg-subtle py-8 text-center">
                      No ASNs recorded for country {selectedCountry}.
                    </p>
                  ) : (
                    filteredAsns.slice(0, 8).map((a) => {
                      const isSelected = selectedAsn === a.key
                      return (
                        <div
                          key={a.key}
                          onClick={() => {
                            setSelectedAsn(isSelected ? null : a.key)
                            setSelectedIp(null)
                          }}
                          className={cn(
                            "group cursor-pointer rounded border p-2.5 transition-colors",
                            isSelected
                              ? "border-accent bg-accent-soft/40"
                              : "border-line-soft bg-panel-2/50 hover:bg-panel-2",
                          )}
                        >
                          <div className="flex items-center justify-between text-xs font-medium">
                            <span className="font-mono-id text-fg">{a.label}</span>
                            <span className="font-mono-id text-fg-muted">{a.count} TXs</span>
                          </div>
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-panel">
                            <div
                              className="h-full rounded-full bg-accent/80 transition-all"
                              style={{ width: `${Math.max(a.percentage, 4)}%` }}
                            />
                          </div>
                          <div className="mt-1 flex justify-between text-[11px] text-fg-subtle">
                            <span>{formatBtc(a.volumeBtc)} total volume</span>
                            <span>{a.percentage}% share</span>
                          </div>
                        </div>
                      )
                    })
                  )}
                </PanelBody>
              </Panel>
            </div>

            {/* Port Conformance & Top Broadcasting Nodes */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Port Distributions */}
              <Panel className="lg:col-span-1">
                <PanelHeader
                  title="Port Conformance"
                  subtitle="Source & destination peer ports"
                  icon={<Radio className="size-4" />}
                />
                <PanelBody className="space-y-4">
                  <div>
                    <h4 className="text-[11px] font-semibold uppercase tracking-wider text-fg-subtle mb-2">
                      Source Ports
                    </h4>
                    <div className="space-y-1.5">
                      {data.ports.srcPorts.map((p) => (
                        <div key={p.port} className="flex items-center justify-between rounded border border-line-soft bg-panel-2 px-2.5 py-1.5 text-xs">
                          <span className="font-mono-id text-fg">Port {p.port}</span>
                          <span className="font-mono-id text-fg-subtle">{p.count} events</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-line-soft">
                    <h4 className="text-[11px] font-semibold uppercase tracking-wider text-fg-subtle mb-2">
                      Destination Ports
                    </h4>
                    <div className="space-y-1.5">
                      {data.ports.dstPorts.map((p) => (
                        <div key={p.port} className="flex items-center justify-between rounded border border-line-soft bg-panel-2 px-2.5 py-1.5 text-xs">
                          <span className="font-mono-id text-fg">Port {p.port}</span>
                          <span className="font-mono-id text-fg-subtle">{p.count} events</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </PanelBody>
              </Panel>

              {/* Top Broadcasting Nodes (IPs) */}
              <Panel className="lg:col-span-2">
                <PanelHeader
                  title="Broadcasting Nodes (IPs)"
                  subtitle="Select IP node to view associated suspicious transactions"
                  icon={<Network className="size-4" />}
                />
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-line text-left text-[11px] uppercase tracking-wider text-fg-subtle">
                        <th className="px-4 py-2.5 font-medium">IP Address</th>
                        <th className="px-4 py-2.5 font-medium">Country</th>
                        <th className="px-4 py-2.5 font-medium">ASN</th>
                        <th className="px-4 py-2.5 font-medium">TX Count</th>
                        <th className="px-4 py-2.5 font-medium">Volume (BTC)</th>
                        <th className="px-4 py-2.5 font-medium">Max ML Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIps.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-xs text-fg-subtle">
                            No IP addresses match the current filter criteria.
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
                                "cursor-pointer border-b border-line-soft transition-colors last:border-0",
                                isSelected ? "bg-accent-soft/40 border-l-2 border-l-accent" : "hover:bg-panel-2",
                              )}
                            >
                              <td className="px-4 py-3 font-mono-id text-xs text-fg">
                                {ip.ip}
                              </td>
                              <td className="px-4 py-3 font-mono-id text-xs text-fg-muted">
                                {ip.country}
                              </td>
                              <td className="px-4 py-3 font-mono-id text-xs text-fg-subtle">
                                {ip.asn}
                              </td>
                              <td className="px-4 py-3 font-mono-id text-xs tabular-nums text-fg-muted">
                                {ip.txCount}
                              </td>
                              <td className="px-4 py-3 font-mono-id text-xs tabular-nums text-fg">
                                {formatBtc(ip.volumeBtc)}
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className="font-mono-id text-xs font-semibold tabular-nums"
                                  style={{
                                    color: ip.maxRisk >= 65 ? "var(--color-risk-critical)" : "var(--color-risk-low)",
                                  }}
                                >
                                  {ip.maxRisk} / 100
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
            </div>

            {/* Suspicious Network Activity Register */}
            <Panel>
              <PanelHeader
                title="Suspicious Network Activity Register"
                subtitle="Transactions flagged with elevated ML risk and broadcasting telemetry"
                icon={<ShieldAlert className="size-4" />}
                action={
                  <span className="rounded bg-risk-critical-soft border border-risk-critical/30 px-2 py-0.5 text-xs font-semibold text-risk-critical">
                    {filteredSuspiciousEvents.length} Events
                  </span>
                }
              />
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-[11px] uppercase tracking-wider text-fg-subtle">
                      <th className="px-4 py-2.5 font-medium">Transaction</th>
                      <th className="px-4 py-2.5 font-medium">Broadcasting IP</th>
                      <th className="px-4 py-2.5 font-medium">Port</th>
                      <th className="px-4 py-2.5 font-medium">ASN / Org</th>
                      <th className="px-4 py-2.5 font-medium">Country</th>
                      <th className="px-4 py-2.5 font-medium">Behavior Typology</th>
                      <th className="px-4 py-2.5 font-medium">ML Risk</th>
                      <th className="px-4 py-2.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSuspiciousEvents.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-8 text-center text-xs text-fg-subtle">
                          No suspicious network activity recorded for the current filter.
                        </td>
                      </tr>
                    ) : (
                      filteredSuspiciousEvents.map((e) => (
                        <tr
                          key={`${e.txid}-${e.ip}`}
                          onClick={() => navigate(`/investigation/${e.txid}?entityType=transaction`)}
                          className="cursor-pointer border-b border-line-soft transition-colors last:border-0 hover:bg-panel-2"
                        >
                          <td className="px-4 py-3">
                            <MonoId value={e.txid} head={8} tail={6} copyable={false} />
                          </td>
                          <td className="px-4 py-3 font-mono-id text-xs text-fg">
                            {e.ip}
                          </td>
                          <td className="px-4 py-3 font-mono-id text-xs text-fg-subtle">
                            {e.port}
                          </td>
                          <td className="px-4 py-3 font-mono-id text-xs text-fg-muted">
                            {e.asnOrg}
                          </td>
                          <td className="px-4 py-3 font-mono-id text-xs text-fg">
                            {e.country}
                          </td>
                          <td className="px-4 py-3">
                            <span className="rounded border border-line bg-panel-2 px-2 py-0.5 font-mono-id text-[11px] text-fg-subtle">
                              {e.behaviorType || "anomalous"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5">
                              <span
                                className="font-mono-id text-xs font-semibold tabular-nums"
                                style={{ color: severityColorVar(e.severity) }}
                              >
                                {e.riskScore}
                              </span>
                              <SeverityBadge severity={e.severity} />
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              onClick={(evt) => {
                                evt.stopPropagation()
                                navigate(`/investigation/${e.txid}?entityType=transaction`)
                              }}
                              className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                            >
                              Investigate
                              <ExternalLink className="size-3" />
                            </button>
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
