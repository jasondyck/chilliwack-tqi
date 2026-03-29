import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { TimeSlotScore } from '../lib/types'

interface Props {
  data: TimeSlotScore[]
}

export default function TimeProfile({ data }: Props) {
  if (!data || data.length === 0) return null

  const maxScore = Math.max(...data.map((d) => d.Score), 5)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Time-of-Day Profile</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <defs>
              <linearGradient id="tpGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="Label" tick={{ fill: '#64748b', fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis domain={[0, Math.ceil(maxScore * 1.15)]} tick={{ fill: '#64748b', fontSize: 13 }} />
            <Tooltip
              contentStyle={{ borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}
              formatter={(v) => [Number(v).toFixed(1), 'TQI']}
            />
            <Area
              type="monotone"
              dataKey="Score"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#tpGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
