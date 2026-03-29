interface ScoreCardProps {
  label: string
  value: number
}

function colorClass(v: number): string {
  if (v < 25) return 'text-red-600'
  if (v < 50) return 'text-orange-500'
  if (v < 70) return 'text-yellow-500'
  return 'text-green-600'
}

export default function ScoreCard({ label, value }: ScoreCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 text-center">
      <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-5xl font-bold mt-2 ${colorClass(value)}`}>{value.toFixed(1)}</p>
    </div>
  )
}
