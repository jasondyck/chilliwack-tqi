import type { NeighbourhoodScore } from '../lib/types'
import { walkScoreBand } from '../lib/walkscore'

interface Props {
  scores: NeighbourhoodScore[]
}


export default function NeighbourhoodTable({ scores }: Props) {
  const sorted = [...scores].sort((a, b) => b.population - a.population)
  const maxPop = Math.max(...sorted.map((s) => s.population), 1)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Neighbourhood Service Quality</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Neighbourhood scores table">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Neighbourhood</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600 min-w-[160px]">Population</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">TQI</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600 hidden sm:table-cell">Category</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-500">Grid Points</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => {
                const popPct = (s.population / maxPop) * 100
                const band = walkScoreBand(s.tqi)
                return (
                  <tr key={s.name} className={`border-b border-slate-100 ${i % 2 === 1 ? 'bg-slate-50/50' : ''}`}>
                    <td className="px-4 py-3 font-medium text-slate-900">{s.name}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden hidden sm:block">
                          <div className="h-full bg-blue-400 rounded-full" style={{ width: `${popPct}%` }} />
                        </div>
                        <span className="tabular-nums text-slate-700">{s.population.toLocaleString()}</span>
                      </div>
                    </td>
                    <td className={`px-4 py-3 text-right font-bold tabular-nums ${band.text}`}>
                      {s.tqi.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${band.badge}`}>{band.label}</span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-500">
                      {s.grid_point_count.toLocaleString()}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs text-slate-500 mt-2">
        City-wide TQI is population-weighted: neighbourhoods with more residents contribute proportionally more to the overall score.
        Colours follow the Walk Score transit bands on the full 0–100 scale.
      </p>
    </section>
  )
}
