import type { RouteLOS } from '../../lib/types'

interface RouteTableProps {
  routes: RouteLOS[]
}

function gradeColor(grade: string): string {
  switch (grade.toUpperCase()) {
    case 'A': return 'bg-green-600 text-white'
    case 'B': return 'bg-green-400 text-white'
    case 'C': return 'bg-yellow-400 text-gray-900'
    case 'D': return 'bg-orange-500 text-white'
    case 'E': return 'bg-red-400 text-white'
    case 'F': return 'bg-red-600 text-white'
    default: return 'bg-gray-300 text-gray-800'
  }
}

export default function RouteTable({ routes }: RouteTableProps) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Route</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Headway</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">LOS</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Trips</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {routes.map((r) => (
            <tr key={r.route_name}>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.route_name}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{r.route_long_name}</td>
              <td className="px-4 py-3 text-sm text-gray-600 text-right">{r.median_headway_min} min</td>
              <td className="px-4 py-3 text-center">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${gradeColor(r.los_grade)}`}>
                  {r.los_grade}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-600 text-right">{r.trip_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
