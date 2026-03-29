import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from '../lib/api'
import type { PipelineResponse } from '../lib/types'

export function usePipelineResults() {
  return useQuery({
    queryKey: ['pipeline-results'],
    queryFn: () => fetchJSON<PipelineResponse>('/api/results'),
    retry: false,
  })
}
