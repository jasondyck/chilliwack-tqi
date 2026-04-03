import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet'
import type { IsochroneResult } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  isochrones: IsochroneResult[]
}

const bandColors: Record<string, string> = {
  '0-15 min': '#2e7d32',
  '15-30 min': '#4caf50',
  '30-45 min': '#ff9800',
  '45-60 min': '#f44336',
  '60-90 min': '#b71c1c',
}

export default function IsochroneMaps({ isochrones }: Props) {
  if (!isochrones || isochrones.length === 0) return null

  const center: [number, number] = [49.168, -121.951]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Isochrone Maps</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {isochrones.map((iso) => (
          <div key={iso.departure_time} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className={`px-3 py-2 border-b border-slate-200 flex items-center gap-2 ${iso.label === 'AM Peak' ? 'bg-blue-50' : 'bg-violet-50'}`}>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold text-white ${iso.label === 'AM Peak' ? 'bg-blue-500' : 'bg-violet-500'}`}>
                {iso.label}
              </span>
              <span className="text-sm font-semibold text-slate-700">{iso.departure_time} Isochrone</span>
            </div>
            <div style={{ height: 400 }}>
              <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
                <TileLayer
                  attribution='&copy; CARTO'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />
                <LayersControl position="topright">
                  {(iso.geojson as any)?.features?.map((feature: any, i: number) => {
                    const bandName = feature.properties?.band ?? ''
                    const color = feature.properties?.color ?? bandColors[bandName] ?? '#999'
                    return (
                      <LayersControl.Overlay key={i} checked name={bandName}>
                        <GeoJSON
                          data={{ type: 'FeatureCollection', features: [feature] } as any}
                          style={() => ({ fillColor: color, color: color, weight: 0.5, fillOpacity: 0.4 })}
                        />
                      </LayersControl.Overlay>
                    )
                  })}
                </LayersControl>
              </MapContainer>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3 justify-center mt-2 text-[10px] text-slate-500">
        {Object.entries(bandColors).map(([label, color]) => (
          <span key={label} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded inline-block" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </section>
  )
}
