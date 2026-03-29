import { useCallback, useRef, useState } from 'react'
import { subscribeSSE } from '../lib/api'

interface PipelineState {
  running: boolean
  step: string
  pct: number
  message: string
  error: string | null
  tqi: number | null
}

export function usePipeline(onComplete?: () => void) {
  const [state, setState] = useState<PipelineState>({
    running: false,
    step: '',
    pct: 0,
    message: '',
    error: null,
    tqi: null,
  })
  const cancelRef = useRef<(() => void) | null>(null)

  const start = useCallback(() => {
    setState({ running: true, step: '', pct: 0, message: '', error: null, tqi: null })
    cancelRef.current = subscribeSSE(
      '/api/pipeline/run',
      (evt) => setState((s) => ({ ...s, step: evt.step, pct: evt.pct, message: evt.message })),
      (evt) => {
        setState((s) => ({ ...s, running: false, tqi: evt.tqi, pct: 100 }))
        onComplete?.()
      },
      (evt) => setState((s) => ({ ...s, running: false, error: evt.message })),
    )
  }, [onComplete])

  const cancel = useCallback(() => {
    cancelRef.current?.()
    setState((s) => ({ ...s, running: false }))
  }, [])

  return { ...state, start, cancel }
}
