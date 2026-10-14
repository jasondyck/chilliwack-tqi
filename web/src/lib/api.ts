const BASE = ''

export async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function subscribeSSE(
  path: string,
  onProgress: (evt: { step: string; pct: number; message: string }) => void,
  onComplete: (evt: { tqi: number; duration_sec: number }) => void,
  onError: (evt: { message: string }) => void,
): () => void {
  const ctrl = new AbortController()

  fetch(`${BASE}${path}`, { method: 'POST', signal: ctrl.signal })
    .then(async (res) => {
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) return

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7)
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (eventType === 'progress') onProgress(data)
            if (eventType === 'complete') onComplete(data)
            if (eventType === 'error') onError(data)
          }
        }
      }
    })
    .catch(() => {})

  return () => ctrl.abort()
}
