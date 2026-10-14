import type { AmenityResult } from '../lib/types'

interface Props {
  amenities: AmenityResult[]
}

function pctColor(pct: number, threshold: number): string {
  return pct >= threshold ? 'text-emerald-600' : 'text-red-500'
}

export default function AmenityTable({ amenities }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Access to Essential Services</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Amenity access table">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600 sticky left-0 bg-slate-50">Destination</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Category</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">30 min</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">60 min</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Mean Time</th>
              </tr>
            </thead>
            <tbody>
              {amenities.map((a, i) => (
                <tr key={a.name} className={`border-b border-slate-100 ${i % 2 === 1 ? 'bg-slate-50/50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-slate-900 sticky left-0 bg-inherit">{a.name}</td>
                  <td className="px-4 py-3 text-slate-500">{a.category}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${pctColor(a.pct_within_30_min, 25)}`}>
                    {a.pct_within_30_min.toFixed(0)}%
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${pctColor(a.pct_within_60_min, 75)}`}>
                    {a.pct_within_60_min.toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 text-right text-slate-700">
                    {a.mean_travel_time > 0 ? `${a.mean_travel_time.toFixed(0)} min` : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
