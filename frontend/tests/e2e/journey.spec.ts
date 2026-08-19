import { test, expect } from '@playwright/test'

// Full primary-journey test — REQUIRES the live backend running with a real
// Gemini key (uv run python -m src) and the built frontend served at
// :8001/app/. It uploads a CSV, asks an aggregation question, and asserts a
// streamed answer appears and the run lands in history.
//
// Run with:  cd frontend && pnpm build && pnpm test:e2e
// (Start the backend first: uv run alembic upgrade head && uv run python -m src)

// A small deterministic CSV. The average of `revenue` for region "north"
// is (100 + 300) / 2 = 200; overall average revenue is 250.
const CSV = [
  'region,revenue',
  'north,100',
  'south,200',
  'north,300',
  'south,400',
].join('\n')

test('upload a CSV, ask a question, get a streamed answer, see it in history', async ({ page }) => {
  await page.goto('')

  // 1. Upload.
  await page.getByTestId('dropzone').scrollIntoViewIfNeeded()
  await page.setInputFiles('#csv-input', {
    name: 'sales.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(CSV),
  })

  const active = page.getByTestId('active-dataset')
  await expect(active).toBeVisible({ timeout: 30_000 })
  await expect(active).toContainText('sales.csv')

  // 1b. Auto-profiling panel appears on upload. When the backend supplies a
  // real profile (POST /datasets -> profile), the columns render; otherwise the
  // panel still renders its "no profile" state (backend profile is optional).
  const profile = page.getByTestId('profile-panel')
  await expect(profile).toBeVisible({ timeout: 30_000 })
  const columns = profile.getByTestId('profile-column')
  if ((await columns.count()) > 0) {
    await expect(columns.first()).toBeVisible()
    await expect(profile).toContainText('region')
    await expect(profile).toContainText('revenue')
  }

  // 2. Ask a question.
  const input = page.getByTestId('question-input')
  await expect(input).toBeEnabled()
  await input.fill('What is the average revenue?')
  await page.getByTestId('ask-button').click()

  // 3. A streamed assistant answer appears with content.
  const assistant = page.getByTestId('assistant-message').last()
  await expect(assistant).toBeVisible()
  // Wait for streaming to settle and produce non-trivial text.
  await expect
    .poll(async () => (await assistant.innerText()).trim().length, { timeout: 60_000 })
    .toBeGreaterThan(10)

  // The plain-language answer should mention the number 250 (overall average).
  await expect(assistant).toContainText(/250/, { timeout: 60_000 })

  // 4. The run is persisted and shows in history.
  await expect(page.getByTestId('history-list')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('history-list')).toContainText('average revenue')

  // 5. If the agent produced follow-up suggestions, they are clickable chips
  // that submit a fresh question. Charts are best-effort (the agent decides).
  const chips = page.getByTestId('followup-chip')
  if ((await chips.count()) > 0) {
    const turnsBefore = await page.getByTestId('user-message').count()
    await chips.first().click()
    await expect
      .poll(async () => page.getByTestId('user-message').count(), { timeout: 30_000 })
      .toBeGreaterThan(turnsBefore)
  }
})
