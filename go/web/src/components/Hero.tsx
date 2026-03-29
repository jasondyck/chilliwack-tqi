import type { TQIResult } from '../lib/types'

interface Props {
  tqi: TQIResult
  category: string
  desc: string
}

function categoryColor(cat: string): string {
  if (cat.includes('Paradise')) return 'bg-emerald-100 text-emerald-800'
  if (cat.includes('Excellent')) return 'bg-green-100 text-green-800'
  if (cat.includes('Good')) return 'bg-blue-100 text-blue-800'
  if (cat.includes('Some')) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export default function Hero({ tqi, category, desc }: Props) {
  const pct = Math.min(tqi.TQI, 100)

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
      <p className="text-sm text-slate-500 mb-1">British Columbia &gt; Fraser Valley</p>
      <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mb-2">
        Chilliwack Transit Quality Index
      </h1>
      <p className="text-slate-600 mb-6">
        Measuring how well public transit connects the city
      </p>

      <div className="flex flex-col sm:flex-row items-start sm:items-end gap-6">
        <div>
          <p className="text-6xl sm:text-7xl font-extrabold text-slate-900 leading-none">
            {tqi.TQI.toFixed(1)}
            <span className="text-2xl sm:text-3xl font-semibold text-slate-400 ml-1">/ 100</span>
          </p>
          <div className="w-64 h-3 bg-slate-100 rounded-full mt-4 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-red-400 via-amber-400 to-emerald-400"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${categoryColor(category)}`}>
            {category}
          </span>
          <span className="text-sm text-slate-500">{desc}</span>
        </div>
      </div>
    </div>
  )
}
