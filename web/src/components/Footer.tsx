interface Props {
  gridPoints: number
  stops: number
}

export default function Footer({ gridPoints, stops }: Props) {
  return (
    <footer className="border-t border-slate-200 pt-6 mt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">directions_bus</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-700">Chilliwack Transit Quality Index</div>
            <div className="text-xs text-slate-500">v0.1.0</div>
          </div>
        </div>
        <div className="text-xs text-slate-500 italic sm:ml-auto max-w-md">
          Generated {new Date().toLocaleDateString()} from BC Transit GTFS data.
          {gridPoints > 0 && ` ${gridPoints.toLocaleString()} grid points, ${stops} stops analyzed.`}
          {' '}Built with Go + React + Recharts + Leaflet.
        </div>
      </div>
    </footer>
  )
}
