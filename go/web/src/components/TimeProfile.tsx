import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts'
import type { TimeSlotScore, DetailedAnalysis } from '../lib/types'

interface Props {
  data: TimeSlotScore[]
  da?: DetailedAnalysis | null
}

export default function TimeProfile({ data, da }: Props) {
  const labels = data.map((d) => d.Label)
  const amStart = labels.findIndex((l) => l >= '07:00')
  const amEnd = labels.findIndex((l) => l > '09:00')
  const pmStart = labels.findIndex((l) => l >= '15:00')
  const pmEnd = labels.findIndex((l) => l > '18:00')

  const amStartLabel = amStart >= 0 ? labels[amStart] : undefined
  const amEndLabel = amEnd >= 0 ? labels[amEnd] : labels[labels.length - 1]
  const pmStartLabel = pmStart >= 0 ? labels[pmStart] : undefined
  const pmEndLabel = pmEnd >= 0 ? labels[pmEnd] : labels[labels.length - 1]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Time-of-Day Profile</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: 20 }}>
            <defs>
              <linearGradient id="tqiGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {amStartLabel && (
              <ReferenceArea x1={amStartLabel} x2={amEndLabel} fill="#f59e0b" fillOpacity={0.08} label={{ value: 'AM Peak', position: 'insideTopLeft', fontSize: 10, fill: '#92400e' }} />
            )}
            {pmStartLabel && (
              <ReferenceArea x1={pmStartLabel} x2={pmEndLabel} fill="#f59e0b" fillOpacity={0.08} label={{ value: 'PM Peak', position: 'insideTopLeft', fontSize: 10, fill: '#92400e' }} />
            )}
            <XAxis
              dataKey="Label"
              tick={{ fontSize: 11, fill: '#64748b' }}
              interval={Math.max(0, Math.floor(data.length / 16) - 1)}
            />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Area type="monotone" dataKey="Score" stroke="#3b82f6" strokeWidth={2} fill="url(#tqiGrad)" />
          </AreaChart>
        </ResponsiveContainer>

        {da && (
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-3 flex items-center gap-3">
              <span className="material-symbols-outlined text-emerald-500">trending_up</span>
              <div>
                <div className="text-xs text-slate-500">Peak Service</div>
                <div className="text-sm font-bold text-slate-900">{da.peak_slot} — TQI {da.peak_tqi.toFixed(1)}</div>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-red-500 p-3 flex items-center gap-3">
              <span className="material-symbols-outlined text-red-500">trending_down</span>
              <div>
                <div className="text-xs text-slate-500">Lowest Service</div>
                <div className="text-sm font-bold text-slate-900">{da.lowest_slot} — TQI {da.lowest_tqi.toFixed(1)}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
