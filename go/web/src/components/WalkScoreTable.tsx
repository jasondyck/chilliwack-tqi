interface Props {
  currentTQI: number
}

const ranges = [
  { min: 90, max: 100, label: "Rider's Paradise", desc: 'World-class public transportation' },
  { min: 70, max: 89, label: 'Excellent Transit', desc: 'Transit convenient for most trips' },
  { min: 50, max: 69, label: 'Good Transit', desc: 'Many nearby public transportation options' },
  { min: 25, max: 49, label: 'Some Transit', desc: 'A few nearby public transportation options' },
  { min: 0, max: 24, label: 'Minimal Transit', desc: 'It is possible to get on a bus' },
]

export default function WalkScoreTable({ currentTQI }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Walk Score Transit Classification</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Range</th>
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Category</th>
              <th className="text-left px-4 py-3 font-semibold text-slate-600">Description</th>
            </tr>
          </thead>
          <tbody>
            {ranges.map((r) => {
              const active = currentTQI >= r.min && currentTQI <= r.max
              return (
                <tr
                  key={r.label}
                  className={`border-b border-slate-100 ${active ? 'bg-blue-50 font-semibold' : 'hover:bg-slate-50'}`}
                >
                  <td className="px-4 py-3 text-slate-700">
                    {r.min} - {r.max}
                    {active && <span className="ml-2 text-blue-600 text-xs">(current)</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-900">{r.label}</td>
                  <td className="px-4 py-3 text-slate-600">{r.desc}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="px-4 py-3 text-xs text-slate-400 border-t border-slate-200">
          Classification based on Walk Score Transit Score methodology. Source: walkscore.com
        </p>
      </div>
    </section>
  )
}
