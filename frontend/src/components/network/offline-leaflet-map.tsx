import { useEffect, useRef } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import worldGeoJson from "@/assets/world-countries.json"
import type { NetworkMapPoint } from "@/api/types"
import { Maximize2, RotateCcw } from "lucide-react"

interface OfflineLeafletMapProps {
  points: NetworkMapPoint[]
  selectedIp: string | null
  onSelectPoint: (point: NetworkMapPoint) => void
  className?: string
}

export function OfflineLeafletMap({
  points,
  selectedIp,
  onSelectPoint,
  className,
}: OfflineLeafletMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markerLayerRef = useRef<L.LayerGroup | null>(null)
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null)

  // Initialize Map and Offline Vector Basemap once
  useEffect(() => {
    if (!mapContainerRef.current) return

    // Prevent duplicate map instances
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove()
      mapInstanceRef.current = null
    }

    const map = L.map(mapContainerRef.current, {
      center: [20, 0],
      zoom: 2,
      minZoom: 1,
      maxZoom: 9,
      worldCopyJump: true,
      zoomControl: false,
      attributionControl: false,
    })

    // Custom Zoom Control top-left
    L.control.zoom({ position: "topleft" }).addTo(map)

    // Render offline vector world landmasses
    const geoLayer = L.geoJSON(worldGeoJson as any, {
      style: {
        fillColor: "#17202e",
        fillOpacity: 0.95,
        color: "#2a374a",
        weight: 0.8,
      },
    }).addTo(map)

    geoJsonLayerRef.current = geoLayer

    const markerGroup = L.layerGroup().addTo(map)
    markerLayerRef.current = markerGroup
    mapInstanceRef.current = map

    // Fix possible container sizing glitch on initial render
    const timer = setTimeout(() => {
      map.invalidateSize()
    }, 100)

    return () => {
      clearTimeout(timer)
      map.remove()
      mapInstanceRef.current = null
      markerLayerRef.current = null
      geoJsonLayerRef.current = null
    }
  }, [])

  // Update Markers when points or selectedIp change without recreating map
  useEffect(() => {
    const map = mapInstanceRef.current
    const markerGroup = markerLayerRef.current
    if (!map || !markerGroup) return

    markerGroup.clearLayers()

    const validPoints = points.filter(
      (p) => p.isMapped && p.latitude !== null && p.latitude !== undefined && p.longitude !== null && p.longitude !== undefined,
    )

    const latLngs: L.LatLngExpression[] = []

    validPoints.forEach((pt) => {
      const lat = pt.latitude!
      const lon = pt.longitude!
      const isSelected = selectedIp === pt.ip
      latLngs.push([lat, lon])

      // Radius scaled slightly by event volume
      const baseRadius = Math.min(13, Math.max(5, Math.log2(pt.eventCount + 1) * 2.2))
      const radius = isSelected ? baseRadius + 4 : baseRadius

      const marker = L.circleMarker([lat, lon], {
        radius,
        fillColor: isSelected ? "#38bdf8" : "#2563eb",
        color: isSelected ? "#ffffff" : "#60a5fa",
        weight: isSelected ? 2.5 : 1.2,
        fillOpacity: isSelected ? 0.95 : 0.8,
      })

      // Tooltip
      const countryStr = pt.country || "Unknown Country"
      const asnStr = pt.asn ? `${pt.asn} (${pt.asName || "Org"})` : "Unspecified ASN"
      const tooltipContent = `
        <div style="font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; line-height: 1.4; color: #1e293b;">
          <div style="font-weight: 700; font-family: monospace; color: #0f172a; margin-bottom: 2px;">${pt.ip}</div>
          <div style="color: #475569;">${countryStr}</div>
          <div style="color: #64748b; font-size: 10px;">${asnStr}</div>
          <div style="margin-top: 4px; padding-top: 3px; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; gap: 8px;">
            <span style="font-weight: 600; color: #1d4ed8;">${pt.eventCount} events</span>
            <span style="color: #64748b;">${pt.transactionCount} txs</span>
          </div>
        </div>
      `
      marker.bindTooltip(tooltipContent, {
        direction: "top",
        offset: [0, -radius],
        opacity: 0.96,
        className: "custom-leaflet-tooltip",
      })

      marker.on("click", () => {
        onSelectPoint(pt)
      })

      markerGroup.addLayer(marker)
    })

    // If an endpoint is selected, pan smoothly to it
    if (selectedIp) {
      const selectedPt = validPoints.find((p) => p.ip === selectedIp)
      if (selectedPt && selectedPt.latitude != null && selectedPt.longitude != null) {
        map.panTo([selectedPt.latitude as number, selectedPt.longitude as number], { animate: true, duration: 0.5 })
      }
    }
  }, [points, selectedIp, onSelectPoint])

  function handleResetView() {
    if (!mapInstanceRef.current) return
    const validPoints = points.filter((p) => p.isMapped && p.latitude != null && p.longitude != null)
    if (validPoints.length > 0) {
      const bounds = L.latLngBounds(validPoints.map((p) => [p.latitude!, p.longitude!]))
      mapInstanceRef.current.fitBounds(bounds, { maxZoom: 5, padding: [30, 30] })
    } else {
      mapInstanceRef.current.setView([20, 0], 2)
    }
  }

  return (
    <div className={`relative overflow-hidden rounded border border-line ${className || "h-[480px] w-full"}`}>
      {/* Map Canvas with Deep Oceanic Base Color */}
      <div
        ref={mapContainerRef}
        className="h-full w-full bg-[#0a0f18] select-none outline-none"
        style={{ cursor: "grab" }}
      />

      {/* Floating Control: Reset Bounds */}
      <div className="absolute top-3 right-3 z-[1000] flex items-center gap-1.5 rounded bg-panel/90 px-2 py-1 text-xs shadow backdrop-blur-sm border border-line">
        <button
          type="button"
          onClick={handleResetView}
          className="flex items-center gap-1 text-[11px] font-medium text-fg-muted hover:text-fg transition-colors"
          title="Reset map view to all endpoints"
        >
          <RotateCcw className="size-3" />
          <span>Fit All</span>
        </button>
      </div>

      {/* Offline Status Badge in Map Corner */}
      <div className="absolute bottom-2 left-2 z-[1000] rounded bg-[#0f172a]/80 px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider text-slate-400 backdrop-blur-sm border border-slate-700/50">
        OFFLINE VECTOR BASEMAP • 110M
      </div>
    </div>
  )
}
