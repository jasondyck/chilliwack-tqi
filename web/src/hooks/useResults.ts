import { useQuery } from '@tanstack/react-query'
import { fetchJSON, RESULTS_URL } from '../lib/api'
import type { PipelineResponse } from '../lib/types'

export function usePipelineResults() {
  return useQuery({
    queryKey: ['pipeline-results'],
    queryFn: () => fetchJSON<PipelineResponse>(RESULTS_URL),
    retry: false,
    staleTime: Infinity,
  })
}
