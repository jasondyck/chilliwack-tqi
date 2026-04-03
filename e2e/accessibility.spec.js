// @ts-check
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const BASE = 'http://localhost:8080'

test.describe('Accessibility audit', () => {
  test('dashboard has no critical accessibility violations', async ({ page }) => {
    test.setTimeout(60000)
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .exclude('.leaflet-container')
      .analyze()

    const violations = results.violations
    if (violations.length > 0) {
      console.log(`\n=== ${violations.length} accessibility violations found ===\n`)
      for (const v of violations) {
        console.log(`[${v.impact}] ${v.id}: ${v.description}`)
        console.log(`  Help: ${v.helpUrl}`)
        console.log(`  Affected nodes: ${v.nodes.length}`)
        for (const node of v.nodes.slice(0, 3)) {
          console.log(`    - ${node.target.join(' > ')}`)
          console.log(`      ${node.failureSummary}`)
        }
        console.log()
      }
    }

    // Fail on critical/serious violations
    const serious = violations.filter((v) => v.impact === 'critical' || v.impact === 'serious')
    expect(serious, `${serious.length} critical/serious a11y violations`).toHaveLength(0)
  })

  test('headway bars scale linearly with data', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)

    // Get all headway bar widths and their associated values
    const bars = await page.evaluate(() => {
      const barEls = document.querySelectorAll('.bg-slate-100.rounded.relative > div:first-child')
      return Array.from(barEls).map((el) => {
        const style = (el instanceof HTMLElement) ? el.style.width : ''
        const pct = parseFloat(style)
        const text = el.textContent?.trim() ?? ''
        const match = text.match(/(\d+)\s*min/)
        const mins = match ? parseInt(match[1]) : null
        // Also check the sibling for external labels
        const sibling = el.nextElementSibling
        const sibText = sibling?.textContent?.trim() ?? ''
        const sibMatch = sibText.match(/(\d+)\s*min/)
        const finalMins = mins ?? (sibMatch ? parseInt(sibMatch[1]) : null)
        return { pct, mins: finalMins }
      }).filter((b) => b.mins !== null && !isNaN(b.pct))
    })

    console.log('Bar data:', JSON.stringify(bars, null, 2))

    expect(bars.length).toBeGreaterThan(1)

    // Check that ratio of percentages matches ratio of minutes (linear scaling)
    // Compare each pair of bars
    for (let i = 0; i < bars.length; i++) {
      for (let j = i + 1; j < bars.length; j++) {
        const a = bars[i]
        const b = bars[j]
        if (a.mins === 0 || b.mins === 0) continue
        const pctRatio = a.pct / b.pct
        const minRatio = a.mins / b.mins
        const tolerance = 0.15 // 15% tolerance for rounding
        expect(
          Math.abs(pctRatio - minRatio) / Math.max(pctRatio, minRatio),
          `Bar ${i} (${a.mins}min=${a.pct}%) vs Bar ${j} (${b.mins}min=${b.pct}%) ratio mismatch`
        ).toBeLessThan(tolerance)
      }
    }
  })
})
