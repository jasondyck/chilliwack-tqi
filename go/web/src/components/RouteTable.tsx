import type { RouteLOS, SystemLOS } from '../lib/types'

interface Props {
  routes: RouteLOS[]
  systemLos: SystemLOS | null
}

const gradeColors: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-green-100 text-green-700',
  C: 'bg-yellow-100 text-yellow-800',
  D: 'bg-orange-100 text-orange-800',
  E: 'bg-red-100 text-red-800',
  F: 'bg-red-200 text-red-900',
}

export default function RouteTable({ routes, systemLos }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Route-Level Service Quality (TCQSM)</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Route</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Name</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Trips</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Median Headway</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">AM Peak</th>
                <th className="text-center px-4 py-3 font-semibold text-slate-600">LOS Grade</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r) => (
                <tr key={r.route_id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{r.route_name}</td>
                  <td className="px-4 py-3 text-slate-700">{r.route_long_name}</td>
                  <td className="px-4 py-3 text-right text-slate-700">{r.trip_count}</td>
                  <td className="px-4 py-3 text-right text-slate-700">
                    {isFinite(r.median_headway) ? `${r.median_headway.toFixed(0)} min` : '--'}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-700">
                    {r.peak_headway != null ? `${r.peak_headway.toFixed(0)} min` : '--'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${gradeColors[r.los_grade] ?? 'bg-slate-100 text-slate-600'}`}
                    >
                      {r.los_grade}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {systemLos && (
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-xs text-slate-500">
            System summary: {systemLos.n_routes} routes, median headway {systemLos.median_headway.toFixed(0)} min,{' '}
            {systemLos.pct_los_d_or_worse.toFixed(0)}% LOS D or worse
          </div>
        )}
      </div>
      <p className="text-xs text-slate-400 mt-2">
        Grading follows the Transit Capacity and Quality of Service Manual (TCQSM, TCRP Report 165, 3rd Edition).
        Grades A-F are assigned based on median headway: A &le; 10 min, B &le; 14 min, C &le; 20 min, D &le; 30 min, E &le; 60 min, F &gt; 60 min.
      </p>
    </section>
  )
}
