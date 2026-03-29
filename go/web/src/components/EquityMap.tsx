import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet'
import type { EquityResult } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  equity: EquityResult
}

function tqiColor(tqi: number): string {
  if (tqi >= 50) return '#22c55e'
  if (tqi >= 25) return '#f59e0b'
  return '#ef4444'
}

function incomeColor(income: number): string {
  if (income >= 60000) return '#4c1d95'
  if (income >= 40000) return '#7c3aed'
  return '#c4b5fd'
}

export default function EquityMap({ equity }: Props) {
  const center: [number, number] = [49.168, -121.951]
  const geojson = equity.geojson as any

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Equity Overlay</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <p className="text-xs text-slate-500 mb-3">Cross-referenced with census income data by Dissemination Area</p>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 500 }}>
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
          <TileLayer
            attribution='&copy; CARTO'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <LayersControl position="topright">
            <LayersControl.Overlay checked name="TQI by DA">
              <GeoJSON
                data={geojson}
                style={(feature: any) => ({
                  fillColor: tqiColor(feature?.properties?.mean_tqi ?? 0),
                  color: '#475569',
                  weight: 1,
                  fillOpacity: 0.5,
                })}
                onEachFeature={(feature: any, layer: any) => {
                  const p = feature?.properties
                  if (p) {
                    layer.bindPopup(`<b>${p.DGUID}</b><br/>TQI: ${p.mean_tqi?.toFixed(1)}<br/>Income: $${p.median_income?.toLocaleString()}`)
                  }
                }}
              />
            </LayersControl.Overlay>
            <LayersControl.Overlay name="Income by DA">
              <GeoJSON
                data={geojson}
                style={(feature: any) => ({
                  fillColor: incomeColor(feature?.properties?.median_income ?? 0),
                  color: '#475569',
                  weight: 1,
                  fillOpacity: 0.5,
                })}
              />
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
      </div>
      <div className="mt-2 flex items-center justify-center gap-2 text-xs text-slate-500">
        <span className="material-symbols-outlined text-violet-500 text-sm">analytics</span>
        TQI-Income correlation: <span className="font-bold text-violet-600">r = {equity.tqi_income_correlation.toFixed(3)}</span>
      </div>
    </section>
  )
}
