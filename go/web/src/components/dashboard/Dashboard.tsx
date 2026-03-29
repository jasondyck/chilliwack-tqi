import { useQueryClient } from '@tanstack/react-query'
import { useResults, useRoutes } from '../../hooks/useResults'
import { usePipeline } from '../../hooks/usePipeline'
import ScoreCard from './ScoreCard'
import ScoreBreakdown from './ScoreBreakdown'
import TimeProfile from './TimeProfile'
import RouteTable from '../routes/RouteTable'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const { data, isLoading, isError } = useResults()
  const { data: routes } = useRoutes()
  const pipeline = usePipeline(() => {
    queryClient.invalidateQueries({ queryKey: ['results'] })
    queryClient.invalidateQueries({ queryKey: ['routes'] })
  })

  if (isLoading) return <p className="text-gray-600">Loading...</p>

  if (isError || !data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">No results yet. Run the analysis pipeline to generate scores.</p>
        {pipeline.running ? (
          <div className="space-y-2">
            <p className="text-sm text-gray-600">{pipeline.step}: {pipeline.message}</p>
            <div className="w-64 mx-auto bg-gray-200 rounded-full h-3">
              <div className="bg-blue-500 h-3 rounded-full transition-all" style={{ width: `${pipeline.pct}%` }} />
            </div>
            <button onClick={pipeline.cancel} className="text-sm text-red-500 hover:underline">Cancel</button>
          </div>
        ) : (
          <button
            onClick={pipeline.start}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Run Analysis
          </button>
        )}
        {pipeline.error && <p className="text-red-500 mt-2 text-sm">{pipeline.error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <ScoreCard label="TQI" value={data.TQI} />
        <ScoreCard label="Coverage" value={data.CoverageScore} />
        <ScoreCard label="Speed" value={data.SpeedScore} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ScoreBreakdown coverage={data.CoverageScore} speed={data.SpeedScore} />
        <TimeProfile data={data.TimeProfile} />
      </div>
      {routes && routes.length > 0 && <RouteTable routes={routes} />}
    </div>
  )
}
