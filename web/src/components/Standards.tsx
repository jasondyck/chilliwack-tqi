export default function Standards() {
  return (
    <section className="bg-white rounded-xl border border-slate-200 border-l-[6px] border-l-violet-500 p-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-violet-500">menu_book</span>
        <h2 className="text-xl font-bold text-slate-900">Standards &amp; Sources</h2>
      </div>
      <div className="text-sm text-slate-600 leading-relaxed space-y-3">
        <p>
          <strong>Walk Score Transit Score</strong> — walkscore.com methodology for classifying transit service
          quality on a 0-100 scale based on distance to nearby transit and frequency of service.
        </p>
        <p>
          <strong>TCQSM</strong> — Transit Capacity and Quality of Service Manual, TCRP Report 165, 3rd Edition.
          Grades A-F based on median headway: A &le; 10 min, B &le; 14, C &le; 20, D &le; 30, E &le; 60, F &gt; 60.
        </p>
        <p>
          <strong>PTAL</strong> — Public Transport Accessibility Level, Transport for London methodology.
          Measures network density and service frequency within walking distance (640m for bus).
          Grades from 1a (worst) to 6b (best).
        </p>
        <p>
          <strong>RAPTOR</strong> — Round-bAsed Public Transit Optimized Router (Delling et al., 2015).
          Multi-criteria journey planning algorithm operating directly on GTFS timetable data.
        </p>
      </div>
    </section>
  )
}
