// formatGTFSDate turns a GTFS YYYYMMDD string into a readable date.
export function formatGTFSDate(d: string | undefined): string | null {
  if (!d || !/^\d{8}$/.test(d)) return null
  const date = new Date(Number(d.slice(0, 4)), Number(d.slice(4, 6)) - 1, Number(d.slice(6, 8)))
  return date.toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })
}

export function formatTimestamp(ts: string | undefined): string | null {
  if (!ts) return null
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })
}

// niceCeil rounds v up to a "nice" axis maximum (1, 1.5, 2, 2.5, 3, 4, 5, 6,
// 8 or 10 times a power of ten) so charts fit their data with tidy ticks.
export function niceCeil(v: number): number {
  if (!(v > 0)) return 1
  const step = 10 ** Math.floor(Math.log10(v))
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    if (m * step >= v) return m * step
  }
  return 10 * step
}

// niceAxis returns a tidy [0, max] domain and evenly spaced ticks covering v.
export function niceAxis(v: number): { domain: [number, number]; ticks: number[] } {
  const step = niceCeil(niceCeil(v) / 5)
  const max = Math.ceil(v / step - 1e-9) * step || step
  const ticks: number[] = []
  for (let t = 0; t <= max + step / 2; t += step) ticks.push(Number(t.toPrecision(12)))
  return { domain: [0, max], ticks }
}
