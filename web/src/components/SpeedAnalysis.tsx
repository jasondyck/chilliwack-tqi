import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
}

const TSR_COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6']

export default function SpeedAnalysis({ da }: Props) {
  const doughnutData = [
    { name: '< 5 km/h', value: da.tsr_slower_than_walking_pct },
    { name: '5-10 km/h', value: da.tsr_5_to_10_pct },
    { name: '10-20 km/h', value: da.tsr_10_to_20_pct },
    { name: '20+ km/h', value: da.tsr_20_plus_pct },
  ]

  const travelTimeData = [
    { name: 'P10', value: da.travel_time_percentiles?.p10 ?? 0, fill: '#22c55e' },
    { name: 'P25', value: da.travel_time_percentiles?.p25 ?? 0, fill: '#84cc16' },
    { name: 'P50', value: da.travel_time_percentiles?.p50 ?? 0, fill: '#f59e0b' },
    { name: 'P75', value: da.travel_time_percentiles?.p75 ?? 0, fill: '#f97316' },
    { name: 'P90', value: da.travel_time_percentiles?.p90 ?? 0, fill: '#ef4444' },
  ]

  const metricCards = [
    { label: 'Mean TSR (km/h)', value: da.mean_tsr.toFixed(1), accent: 'border-l-4 border-l-amber-500' },
    { label: 'Median TSR (km/h)', value: da.median_tsr.toFixed(1), accent: '' },
    { label: 'Slower Than Walking', value: `${da.tsr_slower_than_walking_pct.toFixed(1)}%`, accent: 'border-l-4 border-l-red-500', textColor: 'text-red-500' },
    { label: 'Mean Trip Duration', value: `${da.mean_travel_time_min.toFixed(0)} min`, accent: '' },
  ]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Speed Analysis</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>

      {/* TSR Doughnut + Metric Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4 mb-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col items-center">
          <div className="relative w-[200px] h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={doughnutData} cx="50%" cy="50%" innerRadius="55%" outerRadius="90%" dataKey="value" startAngle={90} endAngle={-270}>
                  {doughnutData.map((_, i) => (
                    <Cell key={i} fill={TSR_COLORS[i]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-extrabold text-slate-900">{da.mean_tsr.toFixed(1)}</span>
              <span className="text-xs text-slate-500">km/h avg TSR</span>
            </div>
          </div>
          <div className="flex gap-3 mt-2 text-[10px] text-slate-500">
            {doughnutData.map((d, i) => (
              <span key={d.name} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: TSR_COLORS[i] }} />
                {d.name}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {metricCards.map((card) => (
            <div key={card.label} className={`bg-white rounded-xl border border-slate-200 p-4 ${card.accent}`}>
              <div className={`text-2xl sm:text-3xl font-extrabold tabular-nums ${card.textColor ?? 'text-slate-900'}`}>
                {card.value}
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mt-1">
                {card.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Travel Time Distribution */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Travel Time Distribution (minutes)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={travelTimeData} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} label={{ position: 'top', fontSize: 11, fontWeight: 600, fill: '#334155' }}>
              {travelTimeData.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
