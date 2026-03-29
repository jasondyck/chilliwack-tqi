interface Props {
  gridPoints: number
  stops: number
}

export default function Footer({ gridPoints, stops }: Props) {
  return (
    <footer className="border-t border-slate-200 pt-6 pb-4 mt-4">
      <div className="text-center space-y-2 text-xs text-slate-400">
        <p>
          Transit Quality Index methodology based on coverage + speed scoring with RAPTOR routing engine.
          Route grading follows TCQSM (TCRP Report 165). PTAL uses TfL methodology.
        </p>
        <p>
          Data: BC Transit GTFS feed | {gridPoints} grid points | {stops} stops |
          Generated {new Date().toLocaleDateString('en-CA')}
        </p>
        <p>Built with Go + React + Recharts + Leaflet</p>
      </div>
    </footer>
  )
}
