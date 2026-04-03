const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8080';

test.describe('Dashboard (Go frontend) smoke tests', () => {

  test('no JavaScript errors on page', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    expect(errors, 'Page should have no JS errors').toEqual([]);
  });

  test('no NaN or undefined values in rendered text', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const body = await page.textContent('body');
    expect(body).not.toContain('NaN');
    expect(body).not.toContain('undefined');
  });

  test('route table renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Route-Level Service Quality');
    await expect(heading.first()).toBeVisible();
  });

  test('coverage stats section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Coverage Analysis');
    await expect(heading.first()).toBeVisible();
  });

  test('speed analysis section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Speed Analysis');
    await expect(heading.first()).toBeVisible();
  });

  test('time profile section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Time-of-Day Profile');
    await expect(heading.first()).toBeVisible();
  });

  test('reliability section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Temporal Reliability');
    await expect(heading.first()).toBeVisible();
  });

  test('methodology section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Methodology');
    await expect(heading.first()).toBeVisible();
  });

  test('standards section renders', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const heading = page.locator('text=Standards');
    await expect(heading.first()).toBeVisible();
  });

  test('full page screenshot', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);

    await page.screenshot({
      path: `e2e/screenshots/dashboard-full-${test.info().project.name}.png`,
      fullPage: true,
    });
  });
});
