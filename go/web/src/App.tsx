import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePipelineResults } from './hooks/useResults'
import Hero from './components/Hero'
import ScoreCards from './components/ScoreCards'
import Narrative from './components/Narrative'
import ScoreBreakdown from './components/ScoreBreakdown'
import RouteTable from './components/RouteTable'
import TimeProfile from './components/TimeProfile'
import PTALChart from './components/PTALChart'
import AmenityTable from './components/AmenityTable'
import HeatMap from './components/HeatMap'
import CoverageStats from './components/CoverageStats'
import TopOrigins from './components/TopOrigins'
import ReliabilityHistogram from './components/ReliabilityHistogram'
import SpeedAnalysis from './components/SpeedAnalysis'
import WalkScoreTable from './components/WalkScoreTable'
import IsochroneMaps from './components/IsochroneMaps'
import Footer from './components/Footer'

const queryClient = new QueryClient()

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50">
      <div className="text-center space-y-4">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-slate-500 font-medium">Loading analysis results...</p>
      </div>
    </div>
  )
}

function NoResults() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50">
      <div className="text-center space-y-3 max-w-md">
        <span className="material-symbols-outlined text-5xl text-slate-300">info</span>
        <h2 className="text-xl font-semibold text-slate-700">No Results Available</h2>
        <p className="text-slate-500">
          Run the analysis pipeline first, then refresh this page.
        </p>
      </div>
    </div>
  )
}

function Dashboard() {
  const { data, isLoading, isError } = usePipelineResults()

  if (isLoading) return <LoadingScreen />
  if (isError || !data) return <NoResults />

  return (
    <div className="bg-slate-50 min-h-screen font-['Inter']">
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 sm:py-10 space-y-8">
        <Hero tqi={data.tqi} category={data.walkscore_category} desc={data.walkscore_desc} gridPoints={data.grid_points} nStops={data.n_stops} />
        <ScoreCards tqi={data.tqi} />
        {data.narrative && <Narrative paragraphs={data.narrative} />}
        <ScoreBreakdown tqi={data.tqi} />
        {data.route_los && <RouteTable routes={data.route_los} systemLos={data.system_los} />}
        {data.detailed_analysis && (
          <CoverageStats da={data.detailed_analysis} gridPoints={data.grid_points} nStops={data.n_stops} />
        )}
        {data.detailed_analysis && <SpeedAnalysis da={data.detailed_analysis} />}
        <TimeProfile data={data.tqi.TimeProfile} da={data.detailed_analysis} />
        {data.ptal && <PTALChart ptal={data.ptal} />}
        {data.amenities && <AmenityTable amenities={data.amenities} />}
        {data.isochrones && <IsochroneMaps isochrones={data.isochrones} />}
        {data.grid_scores && (
          <HeatMap points={data.grid_scores} routeShapes={data.route_shapes} transitStops={data.transit_stops} />
        )}
        {data.detailed_analysis?.top_origins && <TopOrigins origins={data.detailed_analysis.top_origins} />}
        <WalkScoreTable currentTQI={data.tqi.TQI} />
        {data.detailed_analysis && <ReliabilityHistogram da={data.detailed_analysis} />}
        <Footer gridPoints={data.grid_points} stops={data.n_stops} />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}
