'use client'

import { useState } from 'react'
import { exportRun, pinRun } from '@/lib/api'

interface ExportBarProps {
  runId: string
  // Title used when pinning this run to the dashboard (usually the question).
  title: string
  onPinned: () => void
}

// Actions available on a settled answer: pin it to the dashboard, or export the
// cleaned data / report. Kept compact so it sits under the answer bubble.
export default function ExportBar({ runId, title, onPinned }: ExportBarProps) {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pinned, setPinned] = useState(false)

  async function doExport(format: 'csv' | 'report') {
    setBusy(format)
    setError(null)
    try {
      await exportRun(runId, format)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed.')
    } finally {
      setBusy(null)
    }
  }

  async function doPin() {
    setBusy('pin')
    setError(null)
    try {
      await pinRun(runId, title.slice(0, 120) || 'Pinned answer')
      setPinned(true)
      onPinned()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pin failed.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div data-testid="export-bar" className="mt-3 border-t border-slate-200 pt-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="pin-button"
          disabled={busy !== null || pinned}
          onClick={() => void doPin()}
          className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-50"
        >
          <span aria-hidden>📌</span>
          {pinned ? 'Pinned' : busy === 'pin' ? 'Pinning…' : 'Pin to dashboard'}
        </button>
        <button
          type="button"
          data-testid="export-csv"
          disabled={busy !== null}
          onClick={() => void doExport('csv')}
          className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
        >
          <span aria-hidden>⬇️</span>
          {busy === 'csv' ? 'Exporting…' : 'Export CSV'}
        </button>
        <button
          type="button"
          data-testid="export-report"
          disabled={busy !== null}
          onClick={() => void doExport('report')}
          className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
        >
          <span aria-hidden>📄</span>
          {busy === 'report' ? 'Exporting…' : 'Export report'}
        </button>
      </div>
      {error && (
        <p role="alert" data-testid="export-error" className="mt-1.5 text-[11px] text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
