'use client'

import { useRef, useState } from 'react'
import type { Dataset } from '@/lib/api'
import { uploadDataset } from '@/lib/api'

interface UploadPanelProps {
  active: Dataset | null
  onUploaded: (ds: Dataset) => void
}

export default function UploadPanel({ active, onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  async function handleFile(file: File | undefined) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Only .csv files are supported in Phase 1. (Excel is coming soon.)')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const ds = await uploadDataset(file)
      onUploaded(ds)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <section aria-labelledby="upload-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 id="upload-heading" className="text-sm font-semibold text-slate-800">
        1 · Load data
      </h2>

      <div
        data-testid="dropzone"
        onDragOver={e => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          void handleFile(e.dataTransfer.files?.[0])
        }}
        className={`mt-3 flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors ${
          dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 bg-slate-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          id="csv-input"
          disabled={busy}
          onChange={e => void handleFile(e.target.files?.[0])}
        />
        <label
          htmlFor="csv-input"
          className={`cursor-pointer rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 focus-within:outline-none ${
            busy ? 'pointer-events-none opacity-60' : ''
          }`}
        >
          {busy ? 'Uploading…' : 'Choose CSV file'}
        </label>
        <p className="mt-2 text-xs text-slate-500">or drag &amp; drop a .csv here</p>
      </div>

      {busy && (
        <div data-testid="upload-loading" className="mt-3 flex items-center gap-2 text-sm text-indigo-600">
          <Spinner />
          <span>Loading dataset into memory…</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          data-testid="upload-error"
          className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {active ? (
        <div
          data-testid="active-dataset"
          className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3"
        >
          <div className="flex items-center gap-2">
            <span aria-hidden>✅</span>
            <span className="truncate text-sm font-semibold text-emerald-800">{active.name}</span>
          </div>
          <dl className="mt-2 grid grid-cols-2 gap-2 text-xs text-emerald-700">
            <div>
              <dt className="text-emerald-500">Rows</dt>
              <dd className="font-semibold tabular-nums">{active.row_count.toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-emerald-500">Columns</dt>
              <dd className="font-semibold tabular-nums">{active.column_count.toLocaleString()}</dd>
            </div>
          </dl>
        </div>
      ) : (
        !busy && (
          <p data-testid="upload-empty" className="mt-4 text-xs text-slate-400">
            No dataset loaded yet — upload a CSV to begin.
          </p>
        )
      )}
    </section>
  )
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-current" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
