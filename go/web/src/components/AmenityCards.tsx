import type { AmenityResult } from '../lib/types'

interface Props {
  amenities: AmenityResult[]
}

export default function AmenityCards({ amenities }: Props) {
  if (!amenities || amenities.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Amenity Accessibility</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {amenities.map((a) => (
          <div key={a.name} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <p className="font-semibold text-slate-900 text-sm">{a.name}</p>
            <p className="text-xs text-slate-400 mb-3">{a.category}</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Within 30 min</span>
                <span className="font-medium text-slate-700">{a.pct_within_30_min.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Within 60 min</span>
                <span className="font-medium text-slate-700">{a.pct_within_60_min.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Mean travel time</span>
                <span className="font-medium text-slate-700">{a.mean_travel_time.toFixed(1)} min</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
