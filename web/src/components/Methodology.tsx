export default function Methodology() {
  return (
    <section className="bg-white rounded-xl border border-slate-200 border-l-[6px] border-l-blue-500 p-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-blue-500">lightbulb</span>
        <h2 className="text-xl font-bold text-slate-900">Methodology</h2>
      </div>
      <div className="text-sm text-slate-600 leading-relaxed space-y-3">
        <p>
          The Transit Quality Index (TQI) uses the RAPTOR (Round-bAsed Public Transit Optimized Router) algorithm
          to compute fastest journeys between all origin-destination pairs across multiple departure times.
          A 250m grid covers the study area, with travel times computed to every other grid point.
        </p>
        <p>
          The Transit Speed Ratio (TSR) measures effective door-to-door speed including walking, waiting,
          and in-vehicle time. Coverage scores reflect what fraction of the city is reachable by transit.
          Speed scores compare transit performance against walking. Reliability is measured via the
          coefficient of variation of travel times across departure windows.
        </p>
        <p>
          The overall TQI score (0-100) combines coverage, speed, and reliability into a single index.
          Route-level grading follows the Transit Capacity and Quality of Service Manual (TCQSM).
          Accessibility levels use Transport for London&apos;s PTAL methodology.
        </p>
      </div>
    </section>
  )
}
