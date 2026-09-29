import React, { Component, useEffect, useRef, useState, useMemo, useCallback, type ReactNode } from "react"
import Globe, { GlobeMethods } from "react-globe.gl"
import type { NetworkMapPoint, NetworkMapEdge } from "@/api/types"
import { RotateCcw, ZoomIn, ZoomOut, AlertTriangle, RefreshCw, Server, ArrowRight, ShieldAlert } from "lucide-react"
import { formatNumber } from "@/lib/utils"

export interface NetworkGlobeProps {
  points: NetworkMapPoint[]
  edges?: NetworkMapEdge[]
  selectedIp: string | null
  onSelectPoint: (point: NetworkMapPoint) => void
  className?: string
}

interface MappedPoint extends NetworkMapPoint {
  latitude: number
  longitude: number
}

interface ArcItem {
  srcIp: string
  dstIp: string
  startLat: number
  startLng: number
  endLat: number
  endLng: number
  color: string | [string, string]
  stroke: number
  altitude: number
  dashLength: number
  dashGap: number
  animateTime: number
  isIncoming: boolean
  isOutgoing: boolean
  eventCount: number
  transactionCount: number
}

interface PointItem {
  point: MappedPoint
  lat: number
  lng: number
  radius: number
  color: string
  altitude: number
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

/**
 * Checks whether the current browser session can successfully initialize a WebGL context.
 * Prevents Three.js from throwing unhandled context creation exceptions on headless/unsupported Linux environments.
 */
export function checkWebGLSupport(): { supported: boolean; message?: string } {
  if (typeof window === "undefined") {
    return { supported: false, message: "Browser window environment is not available." }
  }
  try {
    const canvas = document.createElement("canvas")
    const gl =
      canvas.getContext("webgl2") ||
      canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl")
    if (!gl) {
      return {
        supported: false,
        message: "WebGL hardware acceleration is unavailable in this browser session.",
      }
    }
    return { supported: true }
  } catch (err) {
    return {
      supported: false,
      message: err instanceof Error ? err.message : "Failed to initialize WebGL context.",
    }
  }
}

interface GlobeErrorBoundaryProps {
  fallback: (error: Error) => ReactNode
  children: ReactNode
}

interface GlobeErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * React Error Boundary safeguarding the application from unhandled Three.js / WebGL exceptions.
 */
export class GlobeErrorBoundary extends Component<GlobeErrorBoundaryProps, GlobeErrorBoundaryState> {
  constructor(props: GlobeErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): GlobeErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.warn("GlobeErrorBoundary caught Three.js/WebGL runtime error:", error, errorInfo)
  }

  resetError = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return this.props.fallback(this.state.error)
    }
    return this.props.children
  }
}

export function NetworkGlobe({
  points,
  edges = [],
  selectedIp,
  onSelectPoint,
  className,
}: NetworkGlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const globeRef = useRef<GlobeMethods | undefined>(undefined)
  const [dimensions, setDimensions] = useState({ width: 800, height: 540 })
  const [reducedMotion, setReducedMotion] = useState(false)
  const [globeReady, setGlobeReady] = useState(false)

  // WebGL availability check
  const [webGlStatus, setWebGlStatus] = useState<{ supported: boolean; message?: string }>(() =>
    checkWebGLSupport(),
  )

  const handleRetryWebGl = useCallback(() => {
    const status = checkWebGLSupport()
    setWebGlStatus(status)
  }, [])

  // Stable callback ref
  const onSelectPointRef = useRef(onSelectPoint)
  useEffect(() => {
    onSelectPointRef.current = onSelectPoint
  }, [onSelectPoint])

  // Track previous selected IP to only animate camera when selection changes
  const prevSelectedIpRef = useRef<string | null>(null)
  const hasOrientedInitialCamera = useRef(false)

  // Detect prefers-reduced-motion
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    setReducedMotion(mq.matches)
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [])

  // ResizeObserver for responsive container sizing without zero-dimension crashes
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const updateSize = () => {
      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        setDimensions({
          width: Math.max(320, Math.floor(rect.width)),
          height: Math.max(400, Math.floor(rect.height)),
        })
      }
    }

    updateSize()

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setDimensions({
            width: Math.max(320, Math.floor(width)),
            height: Math.max(400, Math.floor(height)),
          })
        }
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
    }
  }, [])

  // Filter only valid mapped points with legitimate finite geographic coordinates
  // Strictly enforce valid latitude [-90, 90] and longitude [-180, 180]
  const validPoints = useMemo<MappedPoint[]>(() => {
    return (points || []).filter(
      (p): p is MappedPoint =>
        p.isMapped === true &&
        p.latitude !== null &&
        p.latitude !== undefined &&
        typeof p.latitude === "number" &&
        isFinite(p.latitude) &&
        p.longitude !== null &&
        p.longitude !== undefined &&
        typeof p.longitude === "number" &&
        isFinite(p.longitude) &&
        p.latitude >= -90 &&
        p.latitude <= 90 &&
        p.longitude >= -180 &&
        p.longitude <= 180 &&
        !(p.latitude === 0 && p.longitude === 0),
    )
  }, [points])

  // Fast coordinate lookup map by IP
  const coordsMap = useMemo(() => {
    const map = new Map<string, MappedPoint>()
    for (const p of validPoints) {
      map.set(p.ip, p)
    }
    return map
  }, [validPoints])

  // Selected point object
  const selectedPoint = useMemo(() => {
    if (!selectedIp) return null
    return coordsMap.get(selectedIp) || null
  }, [selectedIp, coordsMap])

  // Identify connected nodes and edges for the currently selected IP
  const { connectedIps, incomingEdgeMap, outgoingEdgeMap } = useMemo(() => {
    const connected = new Set<string>()
    const inMap = new Map<string, NetworkMapEdge>()
    const outMap = new Map<string, NetworkMapEdge>()

    if (!selectedIp) {
      return { connectedIps: connected, incomingEdgeMap: inMap, outgoingEdgeMap: outMap }
    }

    connected.add(selectedIp)
    for (const edge of edges) {
      if (edge.srcIp === selectedIp && edge.dstIp !== selectedIp) {
        connected.add(edge.dstIp)
        outMap.set(edge.dstIp, edge)
      } else if (edge.dstIp === selectedIp && edge.srcIp !== selectedIp) {
        connected.add(edge.srcIp)
        inMap.set(edge.srcIp, edge)
      }
    }

    return { connectedIps: connected, incomingEdgeMap: inMap, outgoingEdgeMap: outMap }
  }, [selectedIp, edges])

  // Data-driven center coordinates for initial camera orientation
  const centerCoords = useMemo(() => {
    if (validPoints.length === 0) return { lat: 20, lng: 0 }
    let sumLat = 0
    let sumLng = 0
    for (const p of validPoints) {
      sumLat += p.latitude
      sumLng += p.longitude
    }
    return {
      lat: sumLat / validPoints.length,
      lng: sumLng / validPoints.length,
    }
  }, [validPoints])

  // Configure OrbitControls when globe becomes ready
  const handleGlobeReady = useCallback(() => {
    setGlobeReady(true)

    // Orient initial camera to data concentration once on startup safely
    if (
      !hasOrientedInitialCamera.current &&
      globeRef.current &&
      typeof globeRef.current.pointOfView === "function"
    ) {
      try {
        globeRef.current.pointOfView(
          { lat: centerCoords.lat, lng: centerCoords.lng, altitude: 2.2 },
          1000,
        )
        hasOrientedInitialCamera.current = true
      } catch (err) {
        console.warn("Failed to orient camera:", err)
      }
    }
  }, [centerCoords])

  // Animate camera smoothly ONLY when selectedIp changes to a different endpoint
  useEffect(() => {
    if (!globeReady || !globeRef.current || typeof globeRef.current.pointOfView !== "function") return

    if (selectedIp !== prevSelectedIpRef.current) {
      prevSelectedIpRef.current = selectedIp

      if (selectedPoint) {
        try {
          globeRef.current.pointOfView(
            {
              lat: selectedPoint.latitude,
              lng: selectedPoint.longitude,
              altitude: 1.7,
            },
            800,
          )
        } catch (err) {
          console.warn("Failed to animate pointOfView:", err)
        }
      }
    }
  }, [selectedIp, selectedPoint, globeReady])

  // Reset view to initial cluster center
  const handleResetView = useCallback(() => {
    if (!globeRef.current || typeof globeRef.current.pointOfView !== "function") return
    try {
      globeRef.current.pointOfView(
        {
          lat: centerCoords.lat,
          lng: centerCoords.lng,
          altitude: 2.2,
        },
        800,
      )
    } catch {}
  }, [centerCoords])

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    if (!globeRef.current || typeof globeRef.current.pointOfView !== "function") return
    try {
      const pov = globeRef.current.pointOfView()
      globeRef.current.pointOfView(
        { ...pov, altitude: Math.max(0.6, (pov.altitude || 2.2) * 0.75) },
        300,
      )
    } catch {}
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!globeRef.current || typeof globeRef.current.pointOfView !== "function") return
    try {
      const pov = globeRef.current.pointOfView()
      globeRef.current.pointOfView(
        { ...pov, altitude: Math.min(4.0, (pov.altitude || 2.2) * 1.3) },
        300,
      )
    } catch {}
  }, [])

  // Memoized 3D Points Data
  const pointsData = useMemo<PointItem[]>(() => {
    return validPoints.map((pt) => {
      const isSelected = pt.ip === selectedIp
      const isIncoming = selectedIp ? incomingEdgeMap.has(pt.ip) : false
      const isOutgoing = selectedIp ? outgoingEdgeMap.has(pt.ip) : false

      // Base radius scaled by event volume - high-visibility native markers
      const baseRadius = Math.min(0.85, Math.max(0.42, Math.log2(pt.eventCount + 1) * 0.12))

      let color = "#38bdf8"
      let radius = baseRadius
      let altitude = 0.018

      if (isSelected) {
        // Selected IP: Prominent amber/gold beacon
        color = "#f59e0b"
        radius = baseRadius * 2.2
        altitude = 0.045
      } else if (selectedIp) {
        if (isIncoming) {
          // Connected incoming: Emerald green
          color = "#10b981"
          radius = baseRadius * 1.5
          altitude = 0.028
        } else if (isOutgoing) {
          // Connected outgoing: Vivid sky blue
          color = "#0ea5e9"
          radius = baseRadius * 1.5
          altitude = 0.028
        } else {
          // All other mapped endpoints REMAIN VISIBLE on realistic Earth
          color = "#e2e8f0"
          radius = baseRadius * 0.95
          altitude = 0.016
        }
      } else {
        // Global overview (no IP selected):
        color = pt.eventCount > 20 ? "#7dd3fc" : "#38bdf8"
        radius = baseRadius * 1.1
        altitude = 0.02
      }

      return {
        point: pt,
        lat: pt.latitude,
        lng: pt.longitude,
        radius,
        color,
        altitude,
      }
    })
  }, [validPoints, selectedIp, incomingEdgeMap, outgoingEdgeMap])

  // Memoized 3D Directional Network Arcs
  const arcsData = useMemo<ArcItem[]>(() => {
    const items: ArcItem[] = []
    let targetEdges = edges || []

    if (selectedIp) {
      targetEdges = targetEdges
        .filter((e) => e.srcIp === selectedIp || e.dstIp === selectedIp)
        .slice(0, 40)
    } else {
      targetEdges = targetEdges
        .slice()
        .sort((a, b) => (b.eventCount || 0) - (a.eventCount || 0))
        .slice(0, 35)
    }

    for (const edge of targetEdges) {
      const src = coordsMap.get(edge.srcIp)
      const dst = coordsMap.get(edge.dstIp)

      // Skip invalid coordinates or self-connections
      if (!src || !dst || edge.srcIp === edge.dstIp) continue
      if (!isFinite(src.latitude) || !isFinite(src.longitude) || !isFinite(dst.latitude) || !isFinite(dst.longitude)) continue

      const isOutgoing = edge.srcIp === selectedIp
      const isIncoming = edge.dstIp === selectedIp

      const distDeg = Math.hypot(dst.latitude - src.latitude, dst.longitude - src.longitude)
      const arcAltitude = Math.min(0.4, Math.max(0.08, distDeg * 0.0035))

      let stroke = Math.min(2.4, Math.max(1.0, Math.log2(edge.eventCount + 1) * 0.35))
      let color: string | [string, string] = "rgba(56, 189, 248, 0.45)"
      let dashLength = 1
      let dashGap = 0
      let animateTime = 0

      if (isOutgoing) {
        color = ["#38bdf8", "#0284c7"]
        stroke = Math.min(2.8, Math.max(1.6, stroke + 0.6))
        dashLength = 0.95
        dashGap = 0.05
        animateTime = reducedMotion ? 0 : 2400
      } else if (isIncoming) {
        color = ["#10b981", "#34d399"]
        stroke = Math.min(2.8, Math.max(1.6, stroke + 0.6))
        dashLength = 0.4
        dashGap = 0.3
        animateTime = reducedMotion ? 0 : 2000
      }

      items.push({
        srcIp: edge.srcIp,
        dstIp: edge.dstIp,
        startLat: src.latitude,
        startLng: src.longitude,
        endLat: dst.latitude,
        endLng: dst.longitude,
        color,
        stroke,
        altitude: arcAltitude,
        dashLength,
        dashGap,
        animateTime,
        isIncoming,
        isOutgoing,
        eventCount: edge.eventCount,
        transactionCount: edge.transactionCount,
      })
    }

    return items
  }, [edges, coordsMap, selectedIp, reducedMotion])

  // HTML Tooltip for Points
  const getPointTooltip = useCallback((item: object) => {
    const ptItem = item as PointItem
    const pt = ptItem.point
    const country = pt.country || "Unknown Location"
    const asn = pt.asn ? `${pt.asn}${pt.asName ? ` (${pt.asName})` : ""}` : "Unspecified ASN"

    return `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; line-height: 1.4; color: #f8fafc; background: rgba(15, 23, 42, 0.95); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.4); box-shadow: 0 8px 24px rgba(0,0,0,0.6); pointer-events: none; min-width: 170px;">
        <div style="font-weight: 700; font-family: ui-monospace, SFMono-Regular, monospace; color: #38bdf8; font-size: 12px; letter-spacing: 0.02em;">
          ${escapeHtml(pt.ip)}
        </div>
        <div style="color: #cbd5e1; margin-top: 3px; font-weight: 500;">
          ${escapeHtml(country)}
        </div>
        <div style="color: #94a3b8; font-size: 10px; margin-top: 1px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${escapeHtml(asn)}
        </div>
        <div style="margin-top: 6px; padding-top: 5px; border-top: 1px solid rgba(51, 65, 85, 0.8); display: flex; justify-content: space-between; gap: 10px; font-size: 10px;">
          <span style="font-weight: 600; color: #60a5fa;">${pt.eventCount.toLocaleString()} events</span>
          <span style="color: #94a3b8;">${pt.transactionCount.toLocaleString()} txs</span>
        </div>
      </div>
    `
  }, [])

  // HTML Tooltip for Arcs
  const getArcTooltip = useCallback((item: object) => {
    const arc = item as ArcItem
    let flowTitle = "Aggregated Flow"
    let titleColor = "#38bdf8"

    if (arc.isIncoming) {
      flowTitle = "Incoming Flow"
      titleColor = "#34d399"
    } else if (arc.isOutgoing) {
      flowTitle = "Outgoing Flow"
      titleColor = "#38bdf8"
    }

    return `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; line-height: 1.4; color: #f8fafc; background: rgba(15, 23, 42, 0.95); padding: 7px 11px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.35); box-shadow: 0 8px 24px rgba(0,0,0,0.6); pointer-events: none;">
        <div style="font-weight: 600; color: ${titleColor}; font-size: 11px;">
          ${flowTitle}
        </div>
        <div style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 10px; color: #cbd5e1; margin-top: 2px;">
          ${escapeHtml(arc.srcIp)} → ${escapeHtml(arc.dstIp)}
        </div>
        <div style="color: #94a3b8; font-size: 10px; margin-top: 3px;">
          ${arc.eventCount.toLocaleString()} events • ${arc.transactionCount.toLocaleString()} transactions
        </div>
      </div>
    `
  }, [])

  const handlePointClick = useCallback((item: object) => {
    const ptItem = item as PointItem
    onSelectPointRef.current(ptItem.point)
  }, [])

  // Render 2D topology fallback if WebGL is unavailable or failed
  if (!webGlStatus.supported) {
    return (
      <GlobeFallback2D
        points={points}
        selectedIp={selectedIp}
        onSelectPoint={onSelectPoint}
        onRetry={handleRetryWebGl}
        reason={webGlStatus.message}
        className={className}
      />
    )
  }

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-lg border border-line bg-[#030712] ${className || "h-[540px] w-full"}`}
      style={{ minHeight: "540px", position: "relative", width: "100%" }}
    >
      <GlobeErrorBoundary
        fallback={(error) => (
          <GlobeFallback2D
            points={points}
            selectedIp={selectedIp}
            onSelectPoint={onSelectPoint}
            onRetry={handleRetryWebGl}
            reason={error.message}
            className={className}
          />
        )}
      >
        {/* 3D Earth Globe Engine with local offline texture */}
        <Globe
          ref={globeRef as any}
          width={dimensions.width}
          height={dimensions.height}
          globeImageUrl="/textures/earth-blue-marble.jpg"
          backgroundColor="#030712"
          showAtmosphere={true}
          atmosphereColor="#bfdbfe"
          atmosphereAltitude={0.09}
          onGlobeReady={handleGlobeReady}
          // Points layer
          pointsData={pointsData}
          pointLat="lat"
          pointLng="lng"
          pointRadius="radius"
          pointColor="color"
          pointAltitude="altitude"
          pointLabel={getPointTooltip}
          onPointClick={handlePointClick}
          pointsTransitionDuration={300}
          // Arcs layer (curved directional flows)
          arcsData={arcsData}
          arcStartLat="startLat"
          arcStartLng="startLng"
          arcEndLat="endLat"
          arcEndLng="endLng"
          arcColor="color"
          arcStroke="stroke"
          arcAltitude="altitude"
          arcDashLength="dashLength"
          arcDashGap="dashGap"
          arcDashAnimateTime="animateTime"
          arcLabel={getArcTooltip}
          arcsTransitionDuration={300}
        />

        {/* Floating Control Bar: Reset View, Zoom */}
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 rounded-lg bg-panel/90 p-1 text-xs shadow-md backdrop-blur-md border border-line">
          <button
            type="button"
            onClick={handleResetView}
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-fg-muted hover:text-fg hover:bg-muted/60 transition-colors"
            title="Reset globe camera to active network data center"
          >
            <RotateCcw className="size-3" />
            <span>Fit All</span>
          </button>

          <div className="h-3.5 w-px bg-line" />

          <button
            type="button"
            onClick={handleZoomIn}
            className="rounded p-1 text-fg-muted hover:text-fg hover:bg-muted/60 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            className="rounded p-1 text-fg-muted hover:text-fg hover:bg-muted/60 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="size-3.5" />
          </button>
        </div>

        {/* Propagation Legend (Visible when endpoint is selected) */}
        {selectedIp && (
          <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2.5 rounded-lg bg-panel/95 px-3 py-1.5 text-[10px] font-sans shadow-md backdrop-blur-md border border-line text-fg">
            <span className="font-semibold text-fg-subtle uppercase tracking-wider text-[9px]">
              Directional Traffic:
            </span>
            <span className="flex items-center gap-1 font-medium">
              <span className="size-2 rounded-full bg-[#34d399] inline-block shadow-sm" /> Incoming
            </span>
            <span className="flex items-center gap-1 font-medium">
              <span className="size-2 rounded-full bg-[#38bdf8] inline-block shadow-sm" /> Outgoing
            </span>
          </div>
        )}

        {/* Network Intelligence Status Badges */}
        <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2">
          <div className="rounded bg-[#0f172a]/90 px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider text-slate-300 backdrop-blur-md border border-slate-700/60 shadow-xs">
            3D EARTH INTELLIGENCE • LOCAL MMDB
          </div>
          <div className="rounded bg-[#0f172a]/80 px-2 py-1 text-[9px] font-mono text-slate-400 backdrop-blur-md border border-slate-800">
            {validPoints.length} PLOTTED
          </div>
        </div>

        {/* Empty State Banner (if no endpoints have mappable coordinates) */}
        {validPoints.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-xs z-10">
            <div className="rounded-lg border border-line bg-panel/95 p-4 text-center shadow-lg max-w-sm mx-4">
              <p className="text-sm font-semibold text-fg">No Mappable Endpoints</p>
              <p className="mt-1 text-xs text-fg-muted">
                No geolocated coordinates were resolved for observed IPs in the active dataset. Unmapped or private nodes remain available in the roster below.
              </p>
            </div>
          </div>
        )}
      </GlobeErrorBoundary>
    </div>
  )
}

/**
 * High-fidelity 2D Geospatial Distribution fallback for environments without WebGL hardware acceleration.
 * Keeps all data completely functional and offline.
 */
function GlobeFallback2D({
  points,
  selectedIp,
  onSelectPoint,
  onRetry,
  reason,
  className,
}: {
  points: NetworkMapPoint[]
  selectedIp: string | null
  onSelectPoint: (point: NetworkMapPoint) => void
  onRetry: () => void
  reason?: string
  className?: string
}) {
  // Aggregate country breakdown
  const countryDistribution = useMemo(() => {
    const map = new Map<string, { country: string; count: number; eventCount: number; points: NetworkMapPoint[] }>()
    for (const p of points) {
      const c = p.country || "Unmapped / Private"
      const existing = map.get(c) || { country: c, count: 0, eventCount: 0, points: [] }
      existing.count += 1
      existing.eventCount += p.eventCount || 0
      existing.points.push(p)
      map.set(c, existing)
    }
    return Array.from(map.values()).sort((a, b) => b.eventCount - a.eventCount)
  }, [points])

  const totalEvents = useMemo(() => {
    return points.reduce((acc, p) => acc + (p.eventCount || 0), 0)
  }, [points])

  return (
    <div
      className={`relative flex flex-col justify-between overflow-hidden rounded-lg border border-line bg-panel p-5 font-sans ${className || "h-[540px] w-full"}`}
      style={{ minHeight: "540px" }}
    >
      {/* Top Banner: WebGL Fallback Notification */}
      <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="size-4 shrink-0 mt-0.5 text-amber-600" />
            <div>
              <p className="font-semibold text-xs text-fg">
                3D Globe Fallback Mode (WebGL Unavailable)
              </p>
              <p className="mt-0.5 text-[11px] text-fg-muted">
                {reason || "WebGL hardware acceleration is not active in this environment."} Displaying offline 2D geospatial telemetry. All endpoint metrics, ASN details, and transaction links remain fully active below.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1 shrink-0 rounded border border-line bg-panel px-2.5 py-1 text-[11px] font-medium text-fg hover:bg-muted transition-colors"
            title="Attempt WebGL context initialization again"
          >
            <RefreshCw className="size-3" />
            <span>Retry 3D</span>
          </button>
        </div>
      </div>

      {/* Middle: 2D Country & Regional Distribution Grid */}
      <div className="mt-4 flex-1 overflow-y-auto space-y-4 pr-1">
        <div className="flex items-center justify-between border-b border-line pb-2">
          <span className="text-xs font-semibold text-fg">Geographic Jurisdiction Distribution</span>
          <span className="text-[11px] text-fg-muted font-mono">
            {countryDistribution.length} regions • {points.length} endpoints
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {countryDistribution.slice(0, 10).map((cd) => {
            const pct = totalEvents > 0 ? (cd.eventCount / totalEvents) * 100 : 0
            const hasSelectedIp = cd.points.some((p) => p.ip === selectedIp)

            return (
              <div
                key={cd.country}
                className={`rounded border p-2.5 text-xs transition-colors cursor-pointer ${
                  hasSelectedIp
                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                    : "border-line bg-panel-2 hover:border-line-strong"
                }`}
                onClick={() => {
                  if (cd.points.length > 0) {
                    onSelectPoint(cd.points[0])
                  }
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-fg truncate">{cd.country}</span>
                  <span className="font-mono text-[11px] text-fg-muted font-medium">
                    {cd.count} {cd.count === 1 ? "IP" : "IPs"} ({formatNumber(cd.eventCount)} evts)
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-[#173B63] transition-all"
                    style={{ width: `${Math.max(pct, 4)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Bottom Bar: Node quick selection summary */}
      <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-[11px] text-fg-muted">
        <span className="font-mono">
          OFFLINE MMDB ENRICHMENT ACTIVE • 100% AIR-GAPPED
        </span>
        <span>
          Select any endpoint in the table below to inspect forensic routing telemetry
        </span>
      </div>
    </div>
  )
}
