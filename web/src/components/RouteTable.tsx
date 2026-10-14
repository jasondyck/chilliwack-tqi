import type { RouteLOS, SystemLOS } from '../lib/types'

interface Props {
  routes: RouteLOS[]
  systemLos: SystemLOS | null
}

const barColors: Record<string, string> = {
  A: '#059669', B: '#22c55e', C: '#84cc16',
  D: '#f59e0b', E: '#f97316', F: '#e11d48',
}

const barTextColors: Record<string, string> = {
  A: 'text-white', B: 'text-white', C: 'text-slate-900',
  D: 'text-slate-900', E: 'text-slate-900', F: 'text-white',
}

const badgeBg: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-green-100 text-green-700',
  C: 'bg-lime-100 text-lime-700',
  D: 'bg-amber-100 text-amber-800',
  E: 'bg-orange-100 text-orange-800',
  F: 'bg-red-100 text-red-800',
}

const gradeRef = [
  { grade: 'A', range: '≤ 10 min', desc: "Passengers don't need schedule", color: 'text-emerald-400' },
  { grade: 'B', range: '≤ 14 min', desc: 'Frequent service', color: 'text-green-400' },
  { grade: 'C', range: '≤ 20 min', desc: 'Maximum desirable wait', color: 'text-lime-400' },
  { grade: 'D', range: '≤ 30 min', desc: 'Unattractive to choice riders', color: 'text-amber-400' },
  { grade: 'E', range: '≤ 60 min', desc: 'Minimal service', color: 'text-orange-400' },
  { grade: 'F', range: '> 60 min', desc: 'Unattractive to all', color: 'text-rose-400' },
]

export default function RouteTable({ routes, systemLos }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Route-Level Service Quality (TCQSM)</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px]">
          {/* Headway bars */}
          <div className="p-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Headway by route chart">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Headway by Route</h3>
            <div className="min-w-[360px] space-y-2">
              {(() => {
                const maxHw = Math.max(...routes.map((r) => r.median_headway ?? 0), 1)
                return routes.map((r) => {
                const hw = r.median_headway ?? 0
                const pct = (hw / maxHw) * 100
                const color = barColors[r.los_grade] ?? '#94a3b8'
                return (
                  <div key={r.route_id} className="flex items-center gap-2">
                    <div className="w-9 text-right font-semibold text-sm text-slate-700 shrink-0">{r.route_name}</div>
                    <div className="w-[140px] text-xs text-slate-500 truncate shrink-0 hidden sm:block">{r.route_long_name}</div>
                    <div className="flex-1 h-6 bg-slate-100 rounded relative min-w-[100px]">
                      <div
                        className="absolute left-0 top-0 h-full rounded flex items-center justify-end pr-1.5"
                        style={{ width: `${pct}%`, background: color }}
                      >
                        {pct > 20 && (
                          <span className={`text-[11px] font-bold ${barTextColors[r.los_grade] ?? 'text-white'}`}>{hw.toFixed(0)} min</span>
                        )}
                      </div>
                      {pct <= 20 && (
                        <span className="absolute top-1/2 -translate-y-1/2 text-[11px] font-bold text-slate-600" style={{ left: `calc(${pct}% + 4px)` }}>
                          {hw.toFixed(0)} min
                        </span>
                      )}
                    </div>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${badgeBg[r.los_grade] ?? 'bg-slate-100 text-slate-600'}`}>
                      {r.los_grade}
                    </div>
                  </div>
                )
              })
              })()}
            </div>
          </div>

          {/* Dark sidebar */}
          <div className="bg-slate-900 text-slate-200 p-4 lg:rounded-r-xl">
            {systemLos && (
              <>
                <h3 className="text-sm font-bold text-white mb-2">System Summary</h3>
                <div className="text-xs text-slate-400 space-y-1 mb-4">
                  <div>{systemLos.n_routes} routes</div>
                  <div>Median headway: <span className="text-white font-semibold">{systemLos.median_system_headway.toFixed(0)} min</span></div>
                  <div>Best grade: <span className={gradeRef.find((g) => g.grade === systemLos.best_grade)?.color ?? ''}>{systemLos.best_grade}</span></div>
                  <div>Worst grade: <span className={gradeRef.find((g) => g.grade === systemLos.worst_grade)?.color ?? ''}>{systemLos.worst_grade}</span></div>
                  <div>{systemLos.pct_los_d_or_worse.toFixed(0)}% LOS D or worse</div>
                </div>
              </>
            )}
            <h4 className="text-xs font-semibold text-slate-400 mb-2">TCQSM Reference</h4>
            <table className="w-full text-[11px]">
              <tbody>
                {gradeRef.map((g) => (
                  <tr key={g.grade} className="border-b border-slate-800 hover:bg-slate-800/50">
                    <td className={`py-1 font-bold ${g.color}`}>{g.grade}</td>
                    <td className="py-1 text-slate-400">{g.range}</td>
                    <td className="py-1 text-slate-400">{g.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <p className="text-xs text-slate-500 mt-2">
        Grading follows the Transit Capacity and Quality of Service Manual (TCQSM, TCRP Report 165, 3rd Edition).
      </p>
    </section>
  )
}
