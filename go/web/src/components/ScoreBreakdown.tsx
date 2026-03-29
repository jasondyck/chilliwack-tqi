import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { TQIResult } from '../lib/types'

interface Props {
  tqi: TQIResult
}

export default function ScoreBreakdown({ tqi }: Props) {
  const data = [
    { name: 'Coverage', value: tqi.CoverageScore, color: '#3b82f6' },
    { name: 'Speed', value: tqi.SpeedScore, color: '#10b981' },
    { name: 'Overall TQI', value: tqi.TQI, color: '#f59e0b' },
  ]

  const maxVal = Math.max(...data.map((d) => d.value), 10)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Score Breakdown</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 13 }} />
            <YAxis domain={[0, Math.ceil(maxVal * 1.15)]} tick={{ fill: '#64748b', fontSize: 13 }} />
            <Tooltip
              contentStyle={{ borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}
              formatter={(v) => [Number(v).toFixed(1), 'Score']}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={80}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
