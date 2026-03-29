export interface TQIResponse {
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
  median_headway_min: number
  los_grade: string
  los_description: string
  trip_count: number
}

export interface AmenityResult {
  name: string
  category: string
  lat: number
  lon: number
  pct_within_30min: number
  pct_within_60min: number
  mean_travel_time_min: number
}

export interface CityComparison {
  city: string
  tqi: number
  coverage: number
  speed: number
  grid_points: number
  stops: number
  routes: number
}

export interface ProgressEvent {
  step: string
  pct: number
  message: string
}
