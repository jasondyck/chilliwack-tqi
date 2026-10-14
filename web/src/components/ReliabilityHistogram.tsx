import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
}

export default function ReliabilityHistogram({ da }: Props) {
  const hist = da.reliability_histogram
  if (!hist || hist.counts.length === 0) return null

  const chartData = hist.labels.map((label, i) => ({
    label,
    count: hist.counts[i],
  }))

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Temporal Reliability</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <p className="text-xs text-slate-500 mb-3">Lower CV = more predictable trip times</p>
        <ResponsiveContainer width="100%" height={256}>
          <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: '#64748b' }}
              interval={Math.max(0, Math.floor(chartData.length / 10) - 1)}
              label={{ value: 'Coefficient of Variation', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#94a3b8' }}
            />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} label={{ value: 'Grid Points', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#94a3b8' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
