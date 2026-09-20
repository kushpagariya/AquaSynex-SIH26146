import { useEffect, useRef, useState, useMemo, useCallback } from "react"
import Globe, { GlobeMethods } from "react-globe.gl"
import type { NetworkMapPoint, NetworkMapEdge } from "@/api/types"
import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react"

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
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    setReducedMotion(mq.matches)
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [])

  // ResizeObserver for responsive container sizing without re-instantiating the globe
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const updateSize = () => {
      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        setDimensions({
          width: Math.floor(rect.width),
          height: Math.floor(rect.height),
        })
      }
    }

    updateSize()

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setDimensions({
            width: Math.floor(width),
            height: Math.floor(height),
          })
        }
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
    }
  }, [])

  // Filter only valid mapped points with legitimate geographic coordinates
  // Strictly enforce: no 0,0 unknown plotting, no missing coordinates
  const validPoints = useMemo<MappedPoint[]>(() => {
    return points.filter(
      (p): p is MappedPoint =>
        p.isMapped === true &&
        p.latitude !== null &&
        p.latitude !== undefined &&
        !isNaN(p.latitude) &&
        p.longitude !== null &&
        p.longitude !== undefined &&
        !isNaN(p.longitude) &&
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

    // Orient initial camera to data concentration once on startup
    if (!hasOrientedInitialCamera.current && globeRef.current) {
      globeRef.current.pointOfView(
        { lat: centerCoords.lat, lng: centerCoords.lng, altitude: 2.2 },
        1000,
      )
      hasOrientedInitialCamera.current = true
    }
  }, [centerCoords])

  // Animate camera smoothly ONLY when selectedIp changes to a different endpoint
  useEffect(() => {
    if (!globeReady || !globeRef.current) return

    if (selectedIp !== prevSelectedIpRef.current) {
      prevSelectedIpRef.current = selectedIp

      if (selectedPoint) {
        globeRef.current.pointOfView(
          {
            lat: selectedPoint.latitude,
            lng: selectedPoint.longitude,
            altitude: 1.7,
          },
          800,
        )
      }
    }
  }, [selectedIp, selectedPoint, globeReady])

  // Reset view to initial cluster center
  const handleResetView = useCallback(() => {
    if (!globeRef.current) return
    globeRef.current.pointOfView(
      {
        lat: centerCoords.lat,
        lng: centerCoords.lng,
        altitude: 2.2,
      },
      800,
    )
  }, [centerCoords])

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    if (!globeRef.current) return
    const pov = globeRef.current.pointOfView()
    globeRef.current.pointOfView(
      { ...pov, altitude: Math.max(0.6, (pov.altitude || 2.2) * 0.75) },
      300,
    )
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!globeRef.current) return
    const pov = globeRef.current.pointOfView()
    globeRef.current.pointOfView(
      { ...pov, altitude: Math.min(4.0, (pov.altitude || 2.2) * 1.3) },
      300,
    )
  }, [])

  // Memoized 3D Points Data
  const pointsData = useMemo<PointItem[]>(() => {
    return validPoints.map((pt) => {
      const isSelected = pt.ip === selectedIp
      const isIncoming = selectedIp ? incomingEdgeMap.has(pt.ip) : false
      const isOutgoing = selectedIp ? outgoingEdgeMap.has(pt.ip) : false
      const isConnected = isIncoming || isOutgoing

      // Bounded radius scaled by event volume (never consumes screen)
      const baseRadius = Math.min(0.7, Math.max(0.25, Math.log2(pt.eventCount + 1) * 0.08))
      const radius = isSelected ? baseRadius * 1.8 : isConnected ? baseRadius * 1.3 : baseRadius

      let color = "#38bdf8"
      let altitude = 0.015

      if (isSelected) {
        color = "#ffffff"
        altitude = 0.04
      } else if (selectedIp) {
        if (isIncoming) {
          color = "#34d399" // Emerald green for incoming source
          altitude = 0.025
        } else if (isOutgoing) {
          color = "#60a5fa" // Sky blue for outgoing destination
          altitude = 0.025
        } else {
          // Unrelated endpoint subdued
          color = "rgba(100, 116, 139, 0.25)"
          altitude = 0.008
        }
      } else {
        // Global view: higher traffic endpoints slightly brighter
        color = pt.eventCount > 20 ? "#38bdf8" : "#2563eb"
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
  // Strictly visualizes actual src_ip -> dst_ip relationships with bounded render budget
  const arcsData = useMemo<ArcItem[]>(() => {
    const items: ArcItem[] = []

    // When an endpoint is selected: prioritize flows connected to it (up to 40 max)
    // When no endpoint is selected: show top 35 global flows sorted by event volume
    let targetEdges = edges

    if (selectedIp) {
      targetEdges = edges
        .filter((e) => e.srcIp === selectedIp || e.dstIp === selectedIp)
        .slice(0, 40)
    } else {
      targetEdges = edges
        .slice()
        .sort((a, b) => (b.eventCount || 0) - (a.eventCount || 0))
        .slice(0, 35)
    }

    for (const edge of targetEdges) {
      const src = coordsMap.get(edge.srcIp)
      const dst = coordsMap.get(edge.dstIp)

      // Skip invalid coordinates or self-connections
      if (!src || !dst || edge.srcIp === edge.dstIp) continue

      const isOutgoing = edge.srcIp === selectedIp
      const isIncoming = edge.dstIp === selectedIp

      const distDeg = Math.hypot(dst.latitude - src.latitude, dst.longitude - src.longitude)
      const arcAltitude = Math.min(0.4, Math.max(0.08, distDeg * 0.0035))

      let stroke = Math.min(2.4, Math.max(1.0, Math.log2(edge.eventCount + 1) * 0.35))
      let color: string | [string, string] = "rgba(56, 189, 248, 0.45)"
      let dashLength = 1
      let dashGap = 0
      let animateTime = 0 // Static by default to ensure maximum performance

      if (isOutgoing) {
        // Outgoing: Solid-feel sky blue
        color = ["#38bdf8", "#0284c7"]
        stroke = Math.min(2.8, Math.max(1.6, stroke + 0.6))
        dashLength = 0.95
        dashGap = 0.05
        animateTime = reducedMotion ? 0 : 2400
      } else if (isIncoming) {
        // Incoming: Distinct dashed emerald green
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

  // HTML Tooltip for Points (real data only, never fabricated)
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

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-lg border border-line bg-[#030712] ${className || "h-[540px] w-full"}`}
      style={{ minHeight: "540px", position: "relative", width: "100%" }}
    >
      {/* 3D Earth Globe Engine */}
      <Globe
        ref={globeRef as any}
        width={dimensions.width}
        height={dimensions.height}
        globeImageUrl="/textures/earth-night.jpg"
        backgroundColor="#030712"
        showAtmosphere={true}
        atmosphereColor="#38bdf8"
        atmosphereAltitude={0.15}
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
        {/* Reset Camera to Network Data Center */}
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

        {/* Zoom Controls */}
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
            <span className="size-2 rounded-full bg-[#34d399] inline-block shadow-sm" /> Incoming (Emerald Dashed)
          </span>
          <span className="flex items-center gap-1 font-medium">
            <span className="size-2 rounded-full bg-[#38bdf8] inline-block shadow-sm" /> Outgoing (Sky Solid)
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
    </div>
  )
}
