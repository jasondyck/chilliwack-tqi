import type { TQIResult } from '../lib/types'

interface Props {
  tqi: TQIResult
}

interface CardDef {
  label: string
  value: string
  desc: string
  icon: string
  color: string
  bg: string
  hoverBorder: string
}

export default function ScoreCards({ tqi }: Props) {
  const cards: CardDef[] = [
    {
      label: 'Overall TQI',
      value: tqi.TQI.toFixed(1),
      desc: '50% coverage + 50% speed',
      icon: 'star',
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      hoverBorder: 'hover:border-amber-400',
    },
    {
      label: 'Coverage',
      value: tqi.CoverageScore.toFixed(1),
      desc: 'Reachability across the network',
      icon: 'location_on',
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      hoverBorder: 'hover:border-blue-400',
    },
    {
      label: 'Speed',
      value: tqi.SpeedScore.toFixed(1),
      desc: 'Competitiveness vs. driving',
      icon: 'speed',
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      hoverBorder: 'hover:border-emerald-400',
    },
    {
      label: 'Reliability CV',
      value: tqi.ReliabilityCV.toFixed(4),
      desc: 'Travel time consistency',
      icon: 'schedule',
      color: 'text-violet-600',
      bg: 'bg-violet-50',
      hoverBorder: 'hover:border-violet-400',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className={`bg-white rounded-xl border border-slate-200 shadow-sm p-6 transition-colors ${c.hoverBorder}`}>
          <div className={`w-10 h-10 rounded-lg ${c.bg} flex items-center justify-center mb-3`}>
            <span className={`material-symbols-outlined ${c.color} text-xl`}>{c.icon}</span>
          </div>
          <p className="text-sm font-medium text-slate-500">{c.label}</p>
          <p className={`text-2xl font-bold ${c.color} mt-1`}>{c.value}</p>
          <p className="text-xs text-slate-400 mt-1">{c.desc}</p>
        </div>
      ))}
    </div>
  )
}
