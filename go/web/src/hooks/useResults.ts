import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from '../lib/api'
import type { TQIResponse, RouteLOS, AmenityResult } from '../lib/types'

interface PipelineResponse {
  tqi: TQIResponse
  route_los: RouteLOS[] | null
  grid_points: number
  n_stops: number
}

export function useResults() {
  return useQuery({
    queryKey: ['results'],
    queryFn: async () => {
      const res = await fetchJSON<PipelineResponse>('/api/results')
      return res.tqi
    },
    retry: false,
  })
}
export function useRoutes() {
  return useQuery({
    queryKey: ['routes'],
    queryFn: async () => {
      const res = await fetchJSON<PipelineResponse>('/api/results')
      return res.route_los || []
    },
    retry: false,
  })
}
export function useAmenities() {
  return useQuery({ queryKey: ['amenities'], queryFn: () => fetchJSON<AmenityResult[]>('/api/results/amenities'), retry: false })
}
