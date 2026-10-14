import type { ResultsMeta } from '../lib/types'
import { formatGTFSDate, formatTimestamp } from '../lib/format'

interface Props {
  gridPoints: number
  stops: number
  meta?: ResultsMeta
}

export default function Footer({ gridPoints, stops, meta }: Props) {
  const generated = formatTimestamp(meta?.generated_at)
  const serviceDate = formatGTFSDate(meta?.service_date)
  const feedStart = formatGTFSDate(meta?.feed_start_date)
  const feedEnd = formatGTFSDate(meta?.feed_end_date)
  return (
    <footer className="border-t border-slate-200 pt-6 mt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">directions_bus</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-700">Chilliwack Transit Quality Index</div>
            <div className="text-xs text-slate-500">
              <a className="underline hover:text-slate-700" href="https://github.com/jasondyck/chilliwack-tqi">Source on GitHub</a>
            </div>
          </div>
        </div>
        <div className="text-xs text-slate-500 italic sm:ml-auto max-w-md">
          {serviceDate ? `Data as of ${serviceDate}` : 'Built from BC Transit GTFS data'}
          {generated && ` · generated ${generated}`}.
          {feedStart && feedEnd && ` GTFS feed valid ${feedStart} – ${feedEnd}.`}
          {gridPoints > 0 && ` ${gridPoints.toLocaleString()} grid points, ${stops} stops analyzed.`}
          {' '}Built with Go + React + Recharts + Leaflet.
        </div>
      </div>
    </footer>
  )
}
