import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { GridScorePoint } from '../lib/types'

interface Props {
  points: GridScorePoint[]
}

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'

function scoreColor(score: number): string {
  if (score >= 50) return '#10b981'
  if (score >= 25) return '#f59e0b'
  if (score > 0) return '#ef4444'
  return '#d1d5db'
}

export default function HeatMap({ points }: Props) {
  if (!points || points.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Coverage Heatmap</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div style={{ height: 500 }}>
          <MapContainer
            center={[49.168, -121.951]}
            zoom={12}
            scrollWheelZoom={true}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
            {points.map((pt, i) => (
              <CircleMarker
                key={i}
                center={[pt.lat, pt.lon]}
                radius={5}
                pathOptions={{
                  fillColor: scoreColor(pt.score),
                  fillOpacity: 0.7,
                  color: scoreColor(pt.score),
                  weight: 0.5,
                  opacity: 0.8,
                }}
              >
                <Tooltip>Score: {pt.score.toFixed(1)}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
        <div className="px-4 py-3 border-t border-slate-200 flex items-center gap-4 text-xs text-slate-500">
          <span>Legend:</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> 0 - 24</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> 25 - 49</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> 50+</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-300 inline-block" /> No service</span>
        </div>
      </div>
    </section>
  )
}
