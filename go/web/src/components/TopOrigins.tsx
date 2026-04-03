import type { TopOrigin } from '../lib/types'

interface Props {
  origins: TopOrigin[]
}

export default function TopOrigins({ origins }: Props) {
  if (!origins || origins.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Best-Connected Locations</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {origins.map((o, i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-blue-500 text-lg">location_on</span>
              <div className="text-sm tabular-nums text-slate-700">
                {o.lat.toFixed(4)}, {o.lon.toFixed(4)}
              </div>
            </div>
            <div className="text-lg font-bold text-blue-600 tabular-nums">
              {o.reachability_pct.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
