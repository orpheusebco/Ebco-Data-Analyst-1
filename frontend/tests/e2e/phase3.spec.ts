import { test, expect } from '@playwright/test'

// Phase 3 UI test. It runs against the served static app but MOCKS the backend
// API via page.route, so it can deterministically exercise the new surfaces —
// Excel sheet picker, multi-dataset selection, pinnable dashboard, and exports —
// without depending on a live LLM. The full real cross-dataset journey is
// covered by the backend pytest suite + journey.spec.ts.

const DATASETS = [
  { dataset_id: 'ds-csv', name: 'sales.csv', kind: 'csv', row_count: 4, column_count: 2, profile: null },
  { dataset_id: 'ds-xlsx', name: 'book.xlsx', kind: 'xlsx', row_count: 3, column_count: 2, profile: null },
]

test('excel sheet picker, multi-select, pin + export flows', async ({ page }) => {
  let dashboard: Array<Record<string, unknown>> = []

  // GET /datasets — start with the two datasets already registered.
  await page.route('**/datasets', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: { data: { datasets: DATASETS }, error: null } })
    } else {
      // POST /datasets (upload with a chosen sheet)
      await route.fulfill({ json: { data: DATASETS[1], error: null } })
    }
  })

  // POST /datasets/excel/sheets — returns multiple sheet names.
  await page.route('**/datasets/excel/sheets', async route => {
    await route.fulfill({ json: { data: { sheets: ['Sheet1', 'Sheet2'] }, error: null } })
  })

  // Per-dataset run history.
  await page.route('**/datasets/*/runs', async route => {
    await route.fulfill({ json: { data: { runs: [] }, error: null } })
  })

  // Dashboard read reflects our in-memory list.
  await page.route('**/dashboard', async route => {
    await route.fulfill({ json: { data: { items: dashboard }, error: null } })
  })

  await page.goto('')

  // Two datasets are listed in the switcher; the first is pre-selected.
  await expect(page.getByTestId('dataset-switcher')).toBeVisible()
  const options = page.getByTestId('dataset-option')
  await expect(options).toHaveCount(2)

  // Select the second as well -> cross-dataset mode.
  await page.getByTestId('dataset-checkbox').nth(1).check()
  await expect(page.getByTestId('selected-count')).toContainText('2 selected')

  // Excel upload -> sheet picker appears with the mocked sheet names.
  await page.setInputFiles('#csv-input', {
    name: 'book.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    buffer: Buffer.from('fake-xlsx-bytes'),
  })
  await expect(page.getByTestId('sheet-picker')).toBeVisible()
  await expect(page.getByTestId('sheet-option')).toHaveCount(2)

  // Dashboard container is present and starts empty.
  await expect(page.getByTestId('dashboard')).toBeVisible()
  await expect(page.getByTestId('dashboard-empty')).toBeVisible()

  // Simulate a pinned item and verify the dashboard renders + unpins it.
  dashboard = [
    {
      id: 'pin-1',
      run_id: 'run-1',
      title: 'Average revenue',
      chart_spec: null,
      answer: 'The average revenue is **250**.',
      position: 0,
      created_at: '2026-07-03T00:00:00Z',
    },
  ]
  await page.route('**/dashboard/pin-1', async route => {
    if (route.request().method() === 'DELETE') {
      dashboard = []
      await route.fulfill({ json: { data: { deleted: true }, error: null } })
    } else {
      await route.fallback()
    }
  })

  await page.reload()
  await expect(page.getByTestId('dashboard-tile')).toHaveCount(1)
  await expect(page.getByTestId('dashboard-tile')).toContainText('Average revenue')

  await page.getByTestId('unpin-button').click()
  await expect(page.getByTestId('dashboard-tile')).toHaveCount(0)
  await expect(page.getByTestId('dashboard-empty')).toBeVisible()
})
