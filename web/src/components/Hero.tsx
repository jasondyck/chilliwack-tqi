import type { ResultsMeta, TQIResult } from '../lib/types'
import { formatGTFSDate } from '../lib/format'

interface Props {
  tqi: TQIResult
  category: string
  populationWeighted: boolean
  meta?: ResultsMeta
}

function categoryColor(cat: string): string {
  if (cat.includes('Paradise') || cat.includes('Excellent')) return 'bg-emerald-100 text-emerald-700'
  if (cat.includes('Good')) return 'bg-blue-100 text-blue-700'
  if (cat.includes('Some')) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

function barGradient(score: number): string {
  if (score >= 70) return 'from-emerald-400 to-emerald-500'
  if (score >= 40) return 'from-amber-400 to-amber-500'
  return 'from-red-400 to-red-500'
}

export default function Hero({ tqi, category, populationWeighted, meta }: Props) {
  const serviceDate = formatGTFSDate(meta?.service_date)
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 relative overflow-hidden">
      <div className="absolute -top-20 -right-20 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl" />
      <div className="relative">
        <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 flex items-center gap-1 mb-4">
          <span className="material-symbols-outlined text-sm text-blue-500">location_on</span>
          British Columbia &gt; Fraser Valley
        </div>
        <h1 className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 mb-2">
          Chilliwack Transit Quality Index
        </h1>
        <p className="text-sm text-slate-500 max-w-xl mb-6">
          {populationWeighted
            ? 'Population-weighted assessment of public transit service quality — coverage, speed, reliability, and accessibility across Chilliwack’s neighbourhoods.'
            : 'Assessment of public transit service quality — coverage, speed, reliability, and accessibility across Chilliwack.'}
        </p>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-700 mb-1">
          {populationWeighted ? 'Population-Weighted Score' : 'City-Wide Score'}
        </div>
        <div className="flex items-baseline gap-2 mb-3">
          <span className="text-5xl sm:text-7xl font-extrabold tabular-nums text-slate-900">
            {tqi.TQI.toFixed(1)}
          </span>
          <span className="text-2xl text-slate-500">/ 100</span>
        </div>
        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden mb-3">
          <div
            className={`h-full rounded-full bg-gradient-to-r ${barGradient(tqi.TQI)}`}
            style={{ width: `${tqi.TQI}%` }}
          />
        </div>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${categoryColor(category)}`}>
          {category}
        </span>
        {serviceDate && (
          <p className="mt-4 text-xs text-slate-500">
            Based on the BC Transit weekday schedule for <span className="font-semibold text-slate-700">{serviceDate}</span>
          </p>
        )}
      </div>
    </div>
  )
}
