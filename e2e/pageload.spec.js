const { test } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const PYTHON_REPORT = 'file://' + path.resolve(__dirname, '../output/report.html');
const GO_DASHBOARD = 'http://localhost:8080';
const ITERATIONS = 3;
const RESULTS_FILE = path.resolve(__dirname, '../bench/pageload-results.json');

async function measureLoad(page, url, label) {
  const timings = [];

  for (let i = 0; i < ITERATIONS; i++) {
    // Clear cache between runs
    const context = page.context();
    await context.clearCookies();

    const start = Date.now();

    await page.goto(url, { waitUntil: 'domcontentloaded' });
    const domReady = Date.now() - start;

    await page.waitForLoadState('load');
    const loaded = Date.now() - start;

    // Wait for main content to be visible (score or heading)
    try {
      await page.locator('h1, h2, [class*="score"], [class*="TQI"]').first().waitFor({ state: 'visible', timeout: 15000 });
    } catch {
      // Some content may not match — that's ok
    }
    const contentVisible = Date.now() - start;

    timings.push({ domReady, loaded, contentVisible });
  }

  return timings;
}

function median(arr) {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

test('benchmark page load: Python report vs Go dashboard', async ({ page }) => {
  test.setTimeout(120000);

  const results = {};

  // Python report (file://)
  const pyTimings = await measureLoad(page, PYTHON_REPORT, 'python');
  results.python = {
    dom_ready_ms: median(pyTimings.map(t => t.domReady)),
    page_load_ms: median(pyTimings.map(t => t.loaded)),
    content_visible_ms: median(pyTimings.map(t => t.contentVisible)),
    raw: pyTimings,
  };

  // Go dashboard (http)
  const goTimings = await measureLoad(page, GO_DASHBOARD, 'go');
  results.go = {
    dom_ready_ms: median(goTimings.map(t => t.domReady)),
    page_load_ms: median(goTimings.map(t => t.loaded)),
    content_visible_ms: median(goTimings.map(t => t.contentVisible)),
    raw: goTimings,
  };

  // Write results
  fs.writeFileSync(RESULTS_FILE, JSON.stringify(results, null, 2));
  console.log('\n=== Page Load Results ===');
  console.log(JSON.stringify(results, null, 2));
});
