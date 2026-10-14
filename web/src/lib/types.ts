import type { FeatureCollection, Geometry } from 'geojson'

export interface PipelineResponse {
  tqi: TQIResult
  route_los: RouteLOS[] | null
  system_los: SystemLOS | null
  ptal: PTALResult | null
  amenities: AmenityResult[] | null
  grid_points: number
  n_stops: number
  grid_scores: GridScorePoint[] | null
  narrative: string[] | null
  walkscore_category: string
  walkscore_desc: string
  detailed_analysis: DetailedAnalysis | null
  isochrones: IsochroneResult[] | null
  equity: EquityResult | null
  route_shapes: RouteShape[] | null
  transit_stops: TransitStop[] | null
  neighbourhood_scores: NeighbourhoodScore[] | null
  neighbourhood_boundaries: FeatureCollection<Geometry, NeighbourhoodProperties> | null
  meta?: ResultsMeta
}

export interface ResultsMeta {
  city: string
  generated_at: string
  feed_version: string
  feed_start_date: string
  feed_end_date: string
  feed_hash: string
  service_date: string
}

export interface NeighbourhoodProperties {
  NAME?: string
}

export interface TQIResult {
  TQI: number
  CoverageScore: number
  SpeedScore: number
  TimeProfile: TimeSlotScore[]
  ReliabilityCV: number
}

export interface TimeSlotScore {
  Label: string
  Score: number
}

export interface RouteLOS {
  route_name: string
  route_long_name: string
  route_id: string
  trip_count: number
  median_headway: number
  peak_headway: number | null
  los_grade: string
  los_description: string
}

export interface SystemLOS {
  n_routes: number
  grade_counts: Record<string, number>
  median_system_headway: number
  best_grade: string
  worst_grade: string
  pct_los_d_or_worse: number
}

export interface PTALResult {
  Values: number[]
  Grades: string[]
}

export interface AmenityResult {
  name: string
  category: string
  lat: number
  lon: number
  pct_within_30_min: number
  pct_within_60_min: number
  mean_travel_time: number
}

export interface GridScorePoint {
  lat: number
  lon: number
  score: number
}

export interface DetailedAnalysis {
  n_origins_with_service: number
  n_transit_desert_origins: number
  transit_desert_pct: number
  n_valid_pairs: number
  n_reachable_pairs: number
  reachability_rate_pct: number
  max_origin_reachability_pct: number
  mean_tsr: number
  median_tsr: number
  tsr_percentiles: Record<string, number>
  tsr_slower_than_walking_pct: number
  tsr_5_to_10_pct: number
  tsr_10_to_20_pct: number
  tsr_20_plus_pct: number
  mean_travel_time_min: number
  median_travel_time_min: number
  travel_time_percentiles: Record<string, number>
  peak_slot: string
  peak_tqi: number
  lowest_slot: string
  lowest_tqi: number
  top_origins: TopOrigin[]
  reliability_histogram: { labels: string[]; counts: number[] }
  ptal_distribution: Record<string, number>
}

export interface TopOrigin {
  lat: number
  lon: number
  reachability_pct: number
}

export interface IsochroneResult {
  departure_time: string
  label: string
  geojson: FeatureCollection<Geometry, IsochroneProperties> | null
}

export interface IsochroneProperties {
  band?: string
  color?: string
}

export interface EquityProperties {
  DGUID?: string
  mean_tqi?: number
  median_income?: number
}

export interface EquityResult {
  geojson: FeatureCollection<Geometry, EquityProperties>
  tqi_income_correlation: number
}

export interface RouteShape {
  route_id: string
  route_name: string
  color: string
  points: number[][]
}

export interface NeighbourhoodScore {
  name: string
  population: number
  tqi: number
  coverage_score: number
  speed_score: number
  grid_point_count: number
}

export interface TransitStop {
  stop_id: string
  stop_name: string
  lat: number
  lon: number
}
