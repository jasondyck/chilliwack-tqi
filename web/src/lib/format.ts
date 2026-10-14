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
