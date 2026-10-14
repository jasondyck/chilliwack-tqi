# Chilliwack TQI — web dashboard

React 19 + TypeScript + Vite single-page dashboard for the Transit Quality Index.
It renders a single `results.json` (written by `tqi run`) that sits beside
`index.html`, so the same build works embedded in the Go binary (`tqi serve`)
and as a static site on GitHub Pages.

```bash
npm ci
npm run dev       # http://localhost:5173 — proxies /results.json to `tqi serve` on :8080
npm run build     # type-check + production build into dist/
npm run lint
npm run e2e       # Playwright smoke + axe accessibility tests against a preview build
```

For `npm run e2e` (and offline dev without the Go server) copy a pipeline
output into `public/results.json` (git-ignored):

```bash
cp ../output/tqi_results.json public/results.json
```

Charts use Recharts and maps use Leaflet; both are lazy-loaded so the headline
score paints before the heavy chunks arrive.
