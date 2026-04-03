import { MapContainer, TileLayer, CircleMarker, Polyline, LayersControl, LayerGroup, Tooltip, GeoJSON } from 'react-leaflet'
import type { GridScorePoint, RouteShape, TransitStop } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  points: GridScorePoint[]
  routeShapes?: RouteShape[] | null
  transitStops?: TransitStop[] | null
  neighbourhoodBoundaries?: unknown | null
}

function scoreColor(score: number): string {
  if (score >= 50) return '#10b981'
  if (score >= 25) return '#f59e0b'
  if (score > 0) return '#ef4444'
  return '#d1d5db'
}

function scoreOpacity(score: number, maxScore: number): number {
  if (maxScore <= 0) return 0.25
  return 0.25 + 0.35 * (score / maxScore)
}

export default function HeatMap({ points, routeShapes, transitStops, neighbourhoodBoundaries }: Props) {
  const center: [number, number] = [49.168, -121.951]
  const maxScore = Math.max(...points.map((p) => p.score), 1)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Spatial Heat Map</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 500 }}>
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
          <TileLayer
            attribution='&copy; <a href="https://carto.com">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <LayersControl position="topright">
            <LayersControl.Overlay checked name="TQI Grid">
              <LayerGroup>
                {points.map((p, i) => (
                  <CircleMarker
                    key={i}
                    center={[p.lat, p.lon]}
                    radius={4}
                    pathOptions={{ color: scoreColor(p.score), fillColor: scoreColor(p.score), fillOpacity: scoreOpacity(p.score, maxScore), weight: 0 }}
                  />
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
            {transitStops && transitStops.length > 0 && (
              <LayersControl.Overlay name="Transit Stops">
                <LayerGroup>
                  {transitStops.map((s) => (
                    <CircleMarker
                      key={s.stop_id}
                      center={[s.lat, s.lon]}
                      radius={3}
                      pathOptions={{ color: '#1e293b', fillColor: '#1e293b', fillOpacity: 0.7, weight: 1 }}
                    >
                      <Tooltip>{s.stop_name}</Tooltip>
                    </CircleMarker>
                  ))}
                </LayerGroup>
              </LayersControl.Overlay>
            )}
            {routeShapes && routeShapes.length > 0 && (
              <LayersControl.Overlay name="Bus Routes">
                <LayerGroup>
                  {routeShapes.map((r) => (
                    <Polyline
                      key={r.route_id}
                      positions={r.points.map((p) => [p[0], p[1]] as [number, number])}
                      pathOptions={{ color: r.color, weight: 3, opacity: 0.7 }}
                    >
                      <Tooltip>{r.route_name}</Tooltip>
                    </Polyline>
                  ))}
                </LayerGroup>
              </LayersControl.Overlay>
            )}
            {neighbourhoodBoundaries != null && (
              <LayersControl.Overlay checked name="Neighbourhoods">
                <GeoJSON
                  data={neighbourhoodBoundaries as any}
                  style={() => ({
                    color: '#475569',
                    weight: 2,
                    fillOpacity: 0,
                    dashArray: '4 4',
                  })}
                  onEachFeature={(feature: any, layer: any) => {
                    const name = feature?.properties?.NAME
                    if (name) {
                      layer.bindTooltip(name, { sticky: true, className: 'text-xs' })
                    }
                  }}
                />
              </LayersControl.Overlay>
            )}
          </LayersControl>
        </MapContainer>
      </div>
      <div className="flex gap-4 justify-center mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> ≥ 50</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> ≥ 25</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> &gt; 0</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-300 inline-block" /> 0</span>
      </div>
    </section>
  )
}
