import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
  gridPoints: number
  nStops: number
}

interface StatCard {
  label: string
  value: string
  accent?: 'red' | 'amber'
}

export default function CoverageStats({ da, gridPoints, nStops }: Props) {
  const cards: StatCard[] = [
    { label: 'Grid Points', value: gridPoints.toLocaleString() },
    { label: 'Transit Stops', value: nStops.toLocaleString() },
    { label: 'Transit Deserts', value: `${da.transit_desert_pct.toFixed(1)}%`, accent: 'red' },
    { label: 'With Service', value: da.n_origins_with_service.toLocaleString() },
    { label: 'OD Reachable', value: `${da.reachability_rate_pct.toFixed(1)}%`, accent: 'amber' },
    { label: 'Best Location', value: `${da.max_origin_reachability_pct.toFixed(1)}%` },
  ]

  const accentStyles = {
    red: { border: 'border-l-4 border-l-red-500', text: 'text-red-500' },
    amber: { border: 'border-l-4 border-l-amber-500', text: 'text-amber-500' },
  }

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Coverage Analysis</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map((card) => {
          const accent = card.accent ? accentStyles[card.accent] : null
          return (
            <div
              key={card.label}
              className={`bg-white rounded-xl border border-slate-200 p-4 min-w-[150px] ${accent?.border ?? ''}`}
            >
              <div className={`text-2xl sm:text-3xl font-extrabold tabular-nums ${accent?.text ?? 'text-slate-900'}`}>
                {card.value}
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mt-1">
                {card.label}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
