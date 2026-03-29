import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { PTALResult } from '../lib/types'

interface Props {
  ptal: PTALResult
}

const gradeOrder = ['1a', '1b', '2', '3', '4', '5', '6a', '6b']
const gradeColors: Record<string, string> = {
  '1a': '#ef4444',
  '1b': '#f97316',
  '2': '#f59e0b',
  '3': '#eab308',
  '4': '#84cc16',
  '5': '#22c55e',
  '6a': '#10b981',
  '6b': '#059669',
}

export default function PTALChart({ ptal }: Props) {
  if (!ptal.Grades || ptal.Grades.length === 0) return null

  const counts: Record<string, number> = {}
  for (const g of gradeOrder) counts[g] = 0
  for (const g of ptal.Grades) {
    if (g in counts) counts[g]++
  }

  const data = gradeOrder.map((g) => ({ grade: g, count: counts[g] }))

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">PTAL Distribution</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="grade" tick={{ fill: '#64748b', fontSize: 13 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 13 }} />
            <Tooltip
              contentStyle={{ borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}
              formatter={(v) => [Number(v), 'Grid Points']}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={60} label={{ position: 'top', fontSize: 11, fontWeight: 600, fill: '#334155' }}>
              {data.map((d) => (
                <Cell key={d.grade} fill={gradeColors[d.grade] ?? '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-slate-400 mt-3">
          Public Transport Accessibility Level (PTAL) using TfL methodology. Higher grades indicate better transit accessibility.
        </p>
      </div>
    </section>
  )
}
