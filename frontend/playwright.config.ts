import { defineConfig, devices } from '@playwright/test'

// E2E tests run against the LIVE app: the FastAPI backend serves the built
// static frontend at http://localhost:8001/app/. Start the backend first
// (`uv run alembic upgrade head && uv run python -m src`) and build the
// frontend (`pnpm build`) before running `pnpm test:e2e`.
//
// Override the base with BASE_URL if serving elsewhere.
const BASE_URL = process.env.BASE_URL ?? 'http://localhost:8001/app/'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
