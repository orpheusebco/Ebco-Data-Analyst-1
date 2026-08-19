'use client'

import { useRef, useState } from 'react'
import type { Dataset } from '@/lib/api'
import { fetchExcelSheets, uploadDataset } from '@/lib/api'

interface UploadPanelProps {
  active: Dataset | null
  onUploaded: (ds: Dataset) => void
}

const CSV_EXTS = ['.csv']
const EXCEL_EXTS = ['.xlsx', '.xls']

function hasExt(name: string, exts: string[]): boolean {
  const lower = name.toLowerCase()
  return exts.some(ext => lower.endsWith(ext))
}

export default function UploadPanel({ active, onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  // When an Excel file is chosen we hold it here and show a sheet picker.
  const [pendingExcel, setPendingExcel] = useState<{ file: File; sheets: string[] } | null>(null)

  function resetInput() {
    if (inputRef.current) inputRef.current.value = ''
  }

  async function doUpload(file: File, sheet?: string) {
    setBusy(true)
    setError(null)
    try {
      const ds = await uploadDataset(file, sheet)
      onUploaded(ds)
      setPendingExcel(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setBusy(false)
      resetInput()
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return
    setPendingExcel(null)
    if (hasExt(file.name, CSV_EXTS)) {
      await doUpload(file)
      return
    }
    if (hasExt(file.name, EXCEL_EXTS)) {
      setBusy(true)
      setError(null)
      try {
        const sheets = await fetchExcelSheets(file)
        if (sheets.length <= 1) {
          // Single-sheet workbook — load it directly, no picker needed.
          await uploadDataset(file, sheets[0])
            .then(onUploaded)
            .catch(e => setError(e instanceof Error ? e.message : 'Upload failed.'))
        } else {
          setPendingExcel({ file, sheets })
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not read workbook.')
      } finally {
        setBusy(false)
        resetInput()
      }
      return
    }
    setError('Unsupported file type. Load a .csv, .xlsx or .xls file.')
    resetInput()
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
          accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
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
          {busy ? 'Uploading…' : 'Choose file'}
        </label>
        <p className="mt-2 text-xs text-slate-500">or drag &amp; drop a .csv, .xlsx or .xls here</p>
      </div>

      {pendingExcel && (
        <div
          data-testid="sheet-picker"
          className="mt-3 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-3"
        >
          <p className="text-xs font-semibold text-indigo-800">
            Pick a sheet from “{pendingExcel.file.name}”
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {pendingExcel.sheets.map(sheet => (
              <button
                key={sheet}
                type="button"
                data-testid="sheet-option"
                disabled={busy}
                onClick={() => void doUpload(pendingExcel.file, sheet)}
                className="rounded-full border border-indigo-300 bg-white px-3 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-50"
              >
                {sheet}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setPendingExcel(null)}
            className="mt-2 text-[11px] font-medium text-indigo-500 hover:underline"
          >
            Cancel
          </button>
        </div>
      )}

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
            No dataset loaded yet — upload a CSV or Excel file to begin.
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
