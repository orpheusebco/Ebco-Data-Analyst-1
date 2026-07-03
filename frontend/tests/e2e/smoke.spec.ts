import { test, expect } from '@playwright/test'

// Smoke test — runs against the live app at :8001/app/. It asserts the page
// renders REAL, STYLED content (not a bare 200), the core controls are present
// and interactive, and the roadmap stubs announce themselves as "coming soon".
// This test does NOT require the agent to answer (no backend LLM call), only
// that the static export is served and wired.

test('workspace loads, is styled, and shows core controls + labelled stubs', async ({ page }) => {
  await page.goto('/')

  // Real content, not a blank shell.
  await expect(page.getByRole('heading', { name: 'Data Analysis Agent' })).toBeVisible()

  // Styled: Tailwind expanded to real CSS, so the header has a computed weight.
  const heading = page.getByRole('heading', { name: 'Data Analysis Agent' })
  const fontWeight = await heading.evaluate(el => getComputedStyle(el).fontWeight)
  expect(Number(fontWeight)).toBeGreaterThanOrEqual(600)

  // Upload control present.
  await expect(page.getByLabel('Choose CSV file')).toBeVisible()
  await expect(page.getByTestId('dropzone')).toBeVisible()

  // Empty states are designed, not blank.
  await expect(page.getByTestId('upload-empty')).toBeVisible()
  await expect(page.getByTestId('chat-empty')).toBeVisible()
  await expect(page.getByTestId('history-empty')).toBeVisible()

  // Chat input exists but is disabled until a dataset loads.
  const input = page.getByTestId('question-input')
  await expect(input).toBeVisible()
  await expect(input).toBeDisabled()

  // Labelled stubs are present and badged as coming soon.
  const badges = page.getByTestId('coming-soon-badge')
  await expect(badges.first()).toBeVisible()
  expect(await badges.count()).toBeGreaterThanOrEqual(6)
  await expect(page.getByText('Excel upload')).toBeVisible()
  await expect(page.getByText('Interactive charts')).toBeVisible()

  // Stub cards are non-interactive placeholders.
  await expect(page.getByTestId('stub-card').first()).toHaveAttribute('aria-disabled', 'true')
})
