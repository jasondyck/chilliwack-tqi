// Walk Score Transit Score bands (walkscore.com), used to label and colour
// any 0–100 score the same way across the dashboard.
export interface WalkScoreBand {
  min: number
  max: number
  label: string
  desc: string
  text: string // text colour class (WCAG AA on white)
  badge: string // pill background + text classes
}

export const WALK_SCORE_BANDS: WalkScoreBand[] = [
  { min: 90, max: 100, label: "Rider's Paradise", desc: 'World-class public transportation', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-700' },
  { min: 70, max: 89, label: 'Excellent Transit', desc: 'Transit convenient for most trips', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-700' },
  { min: 50, max: 69, label: 'Good Transit', desc: 'Many nearby public transportation options', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-700' },
  { min: 25, max: 49, label: 'Some Transit', desc: 'A few nearby public transportation options', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-700' },
  { min: 0, max: 24, label: 'Minimal Transit', desc: 'It is possible to get on a bus', text: 'text-red-700', badge: 'bg-red-100 text-red-700' },
]

// walkScoreBand returns the band a score falls in. Bands are matched on their
// lower bound so fractional scores (e.g. 24.6) land in the right band.
export function walkScoreBand(score: number): WalkScoreBand {
  return WALK_SCORE_BANDS.find((b) => score >= b.min) ?? WALK_SCORE_BANDS[WALK_SCORE_BANDS.length - 1]
}
