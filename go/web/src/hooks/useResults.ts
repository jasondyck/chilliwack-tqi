import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from '../lib/api'
import type { TQIResponse, RouteLOS, AmenityResult } from '../lib/types'

export function useResults() {
  return useQuery({ queryKey: ['results'], queryFn: () => fetchJSON<TQIResponse>('/api/results'), retry: false })
}
export function useRoutes() {
  return useQuery({ queryKey: ['routes'], queryFn: () => fetchJSON<RouteLOS[]>('/api/results/routes'), retry: false })
}
export function useAmenities() {
  return useQuery({ queryKey: ['amenities'], queryFn: () => fetchJSON<AmenityResult[]>('/api/results/amenities'), retry: false })
}
