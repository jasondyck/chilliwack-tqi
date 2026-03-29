interface Props {
  paragraphs: string[]
}

export default function Narrative({ paragraphs }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 border-l-4 border-l-blue-500">
      <div className="flex items-center gap-2 mb-4">
        <span className="material-symbols-outlined text-blue-500">lightbulb</span>
        <h2 className="text-lg font-bold text-slate-900">Analysis Narrative</h2>
      </div>
      <div className="space-y-3">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-slate-700 leading-relaxed">{p}</p>
        ))}
      </div>
    </div>
  )
}
