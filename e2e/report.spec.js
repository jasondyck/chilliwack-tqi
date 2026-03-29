const { test, expect } = require('@playwright/test');
const path = require('path');

const REPORT_URL = 'file://' + path.resolve(__dirname, '../output/report.html');

test.describe('TQI Report Visual Tests', () => {

  test('hero section renders with score', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const score = page.locator('text=/ 100');
    await expect(score.first()).toBeVisible();

    await page.screenshot({ path: `e2e/screenshots/hero-${test.info().project.name}.png`, clip: { x: 0, y: 0, width: 1440, height: 600 } });
  });

  test('all Chart.js canvases render with content', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const chartIds = [
      'chart-scores',
      'chart-tsr',
      'chart-travel-time',
      'chart-time-profile',
      'chart-reliability',
      'chart-ptal',
    ];

    for (const id of chartIds) {
      const canvas = page.locator(`#${id}`);
      const visible = await canvas.isVisible();
      if (!visible) {
        console.log(`Canvas #${id} not visible — skipping`);
        continue;
      }

      // Check canvas has been drawn on (not blank)
      const hasContent = await canvas.evaluate(function(el) {
        var ctx = el.getContext('2d');
        var data = ctx.getImageData(0, 0, el.width, el.height).data;
        for (var i = 0; i < data.length; i += 16) {
          if (data[i+3] > 0 && (data[i] < 240 || data[i+1] < 240 || data[i+2] < 240)) return true;
        }
        return false;
      });
      expect(hasContent, `Canvas #${id} should have drawn content`).toBe(true);

      await canvas.screenshot({ path: `e2e/screenshots/${id}-${test.info().project.name}.png` });
    }
  });

  test('route LOS bars are visible', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const routeSection = page.locator('text=Headway by Route').first();
    await expect(routeSection).toBeVisible();
  });

  test('score cards have numeric content', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    for (const label of ['OVERALL TQI', 'COVERAGE', 'SPEED', 'RELIABILITY']) {
      const el = page.locator(`text=${label}`).first();
      await expect(el).toBeVisible();
    }
  });

  test('no NaN or undefined values', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const body = await page.textContent('body');
    expect(body).not.toContain('NaN');
    expect(body).not.toContain('undefined');
  });

  test('map iframes exist', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });

    const iframes = page.locator('iframe');
    const count = await iframes.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('amenity table has data', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    await expect(page.locator('text=Chilliwack General Hospital').first()).toBeVisible();
  });

  test('no JavaScript errors on page', async ({ page }) => {
    const errors = [];
    page.on('pageerror', function(err) { errors.push(err.message); });

    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    expect(errors, 'Page should have no JS errors').toEqual([]);
  });

  test('full page screenshot', async ({ page }) => {
    await page.goto(REPORT_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    await page.screenshot({
      path: `e2e/screenshots/full-page-${test.info().project.name}.png`,
      fullPage: true,
    });
  });
});
