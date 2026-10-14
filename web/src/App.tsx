import { lazy, Suspense, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePipelineResults } from './hooks/useResults'
import Hero from './components/Hero'
import ScoreCards from './components/ScoreCards'
import NeighbourhoodTable from './components/NeighbourhoodTable'
import Narrative from './components/Narrative'
import WalkScoreTable from './components/WalkScoreTable'
import RouteTable from './components/RouteTable'
import CoverageStats from './components/CoverageStats'
import TopOrigins from './components/TopOrigins'
import AmenityTable from './components/AmenityTable'
import Methodology from './components/Methodology'
import Standards from './components/Standards'
import Footer from './components/Footer'

// Chart (Recharts) and map (Leaflet) components are split into separate
// chunks so the headline score renders before the heavy libraries load.
const ScoreBreakdown = lazy(() => import('./components/ScoreBreakdown'))
const SpeedAnalysis = lazy(() => import('./components/SpeedAnalysis'))
const TimeProfile = lazy(() => import('./components/TimeProfile'))
const PTALChart = lazy(() => import('./components/PTALChart'))
const HeatMap = lazy(() => import('./components/HeatMap'))
const IsochroneMaps = lazy(() => import('./components/IsochroneMaps'))
const EquityMap = lazy(() => import('./components/EquityMap'))
const ReliabilityHistogram = lazy(() => import('./components/ReliabilityHistogram'))

function Deferred({ height, children }: { height: number; children: ReactNode }) {
  return (
    <Suspense
      fallback={<div className="bg-white rounded-xl border border-slate-200 shadow-sm animate-pulse" style={{ height }} />}
    >
      {children}
    </Suspense>
  )
}

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
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 sm:py-10 space-y-8">
        <Hero
          tqi={data.tqi}
          category={data.walkscore_category}
          populationWeighted={!!data.neighbourhood_scores?.length}
          meta={data.meta}
        />
        <ScoreCards tqi={data.tqi} />
        {data.neighbourhood_scores && <NeighbourhoodTable scores={data.neighbourhood_scores} />}
        {data.narrative && <Narrative paragraphs={data.narrative} />}
        <Deferred height={320}><ScoreBreakdown tqi={data.tqi} /></Deferred>
        <WalkScoreTable currentTQI={data.tqi.TQI} />
        {data.route_los && <RouteTable routes={data.route_los} systemLos={data.system_los} />}
        {data.detailed_analysis && (
          <CoverageStats da={data.detailed_analysis} gridPoints={data.grid_points} nStops={data.n_stops} />
        )}
        {data.detailed_analysis && <Deferred height={400}><SpeedAnalysis da={data.detailed_analysis} /></Deferred>}
        <Deferred height={360}><TimeProfile data={data.tqi.TimeProfile} da={data.detailed_analysis} /></Deferred>
        {data.ptal && <Deferred height={360}><PTALChart ptal={data.ptal} /></Deferred>}
        {data.grid_scores && (
          <Deferred height={540}>
            <HeatMap points={data.grid_scores} routeShapes={data.route_shapes} transitStops={data.transit_stops} neighbourhoodBoundaries={data.neighbourhood_boundaries} />
          </Deferred>
        )}
        {data.detailed_analysis?.top_origins && <TopOrigins origins={data.detailed_analysis.top_origins} />}
        {data.amenities && <AmenityTable amenities={data.amenities} />}
        {data.isochrones && <Deferred height={460}><IsochroneMaps isochrones={data.isochrones} /></Deferred>}
        {data.equity && <Deferred height={540}><EquityMap equity={data.equity} /></Deferred>}
        {data.detailed_analysis && <Deferred height={360}><ReliabilityHistogram da={data.detailed_analysis} /></Deferred>}
        <Methodology />
        <Standards />
        <Footer gridPoints={data.grid_points} stops={data.n_stops} meta={data.meta} />
      </main>
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
