import { test, expect } from '@playwright/test'

// Smoke test — runs against the live app at :8001/app/. It asserts the page
// renders REAL, STYLED content (not a bare 200), the core controls are present
// and interactive, and — now that Phase 3 shipped — that NO "coming soon"
// stubs remain: every surface (upload incl. Excel, dataset switcher, dashboard)
// is functional. This test does NOT require the agent to answer (no backend LLM
// call), only that the static export is served and wired.

test('workspace loads, is styled, shows core controls, and has NO stubs', async ({ page }) => {
  await page.goto('')

  // Real content, not a blank shell.
  await expect(page.getByRole('heading', { name: 'Data Analysis Agent' })).toBeVisible()

  // Styled: Tailwind expanded to real CSS, so the header has a computed weight.
  const heading = page.getByRole('heading', { name: 'Data Analysis Agent' })
  const fontWeight = await heading.evaluate(el => getComputedStyle(el).fontWeight)
  expect(Number(fontWeight)).toBeGreaterThanOrEqual(600)

  // Upload control present and accepts CSV + Excel.
  await expect(page.getByLabel('Choose file')).toBeVisible()
  await expect(page.getByTestId('dropzone')).toBeVisible()
  const accept = await page.locator('#csv-input').getAttribute('accept')
  expect(accept).toContain('.csv')
  expect(accept).toContain('.xlsx')
  expect(accept).toContain('.xls')

  // Dataset switcher (multi-file compare) and dashboard containers render.
  await expect(page.getByTestId('dataset-switcher')).toBeVisible()
  await expect(page.getByTestId('dashboard')).toBeVisible()

  // Chat input exists (enabled or disabled depending on whether the live
  // backend already has a dataset loaded — both are valid states).
  const input = page.getByTestId('question-input')
  await expect(input).toBeVisible()

  // NO labelled stubs remain anywhere on the page.
  await expect(page.getByText('Coming soon', { exact: false })).toHaveCount(0)
  await expect(page.getByTestId('stub-card')).toHaveCount(0)
  await expect(page.getByTestId('coming-soon-badge')).toHaveCount(0)

  // The Phase 3 features are now real, not roadmap placeholders.
  await expect(page.getByText('Excel upload')).toHaveCount(0)
  await expect(page.getByText('Multi-file compare')).toHaveCount(0)
  await expect(page.getByText('Pinnable dashboard')).toHaveCount(0)
})
