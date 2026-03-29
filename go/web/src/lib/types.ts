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
  median_headway: number
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
