interface Props {
  currentTQI: number
}

import { WALK_SCORE_BANDS, walkScoreBand } from '../lib/walkscore'

export default function WalkScoreTable({ currentTQI }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Walk Score Transit Classification</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Range</th>
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Description</th>
            </tr>
          </thead>
          <tbody>
            {WALK_SCORE_BANDS.map((r, i) => {
              const active = r === walkScoreBand(currentTQI)
              return (
                <tr
                  key={r.label}
                  className={`border-b border-slate-100 ${active ? 'bg-amber-50 font-semibold' : i % 2 === 1 ? 'bg-slate-50/50' : 'hover:bg-slate-50'}`}
                >
                  <td className="px-4 py-3 text-slate-700">
                    {r.min} - {r.max}
                    {active && <span className="ml-2 text-amber-700 text-xs">(current)</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-900">{r.label}</td>
                  <td className="px-4 py-3 text-slate-600">{r.desc}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="px-4 py-3 text-xs text-slate-500 border-t border-slate-200">
          Classification based on Walk Score Transit Score methodology. Source: walkscore.com
        </p>
      </div>
    </section>
  )
}
