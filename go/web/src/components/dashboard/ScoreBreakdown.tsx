interface ScoreBreakdownProps {
  coverage: number
  speed: number
}

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{value.toFixed(1)}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-4">
        <div
          className={`${color} h-4 rounded-full transition-all`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  )
}

export default function ScoreBreakdown({ coverage, speed }: ScoreBreakdownProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Score Breakdown</h3>
      <Bar label="Coverage" value={coverage} color="bg-blue-500" />
      <Bar label="Speed" value={speed} color="bg-green-500" />
    </div>
  )
}
