// Results live beside index.html: served by `tqi serve` locally and as a
// static file on GitHub Pages.
export const RESULTS_URL = `${import.meta.env.BASE_URL}results.json`

export async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
