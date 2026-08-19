'use client'

import { useState } from 'react'
import type { Run } from '@/lib/api'

interface HistoryPanelProps {
  runs: Run[]
  loading: boolean
  error: string | null
  hasDataset: boolean
}

const STATUS_STYLE: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  needs_clarification: 'bg-amber-100 text-amber-700',
}

export default function HistoryPanel({ runs, loading, error, hasDataset }: HistoryPanelProps) {
  const [openId, setOpenId] = useState<string | null>(null)

  return (
    <section aria-labelledby="history-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 id="history-heading" className="text-sm font-semibold text-slate-800">
        Run history
      </h2>

      {loading && (
        <p data-testid="history-loading" className="mt-3 text-xs text-slate-400">
          Loading history…
        </p>
      )}

      {error && (
        <p role="alert" data-testid="history-error" className="mt-3 text-xs text-red-600">
          {error}
        </p>
      )}

      {!loading && !error && !hasDataset && (
        <p data-testid="history-empty" className="mt-3 text-xs text-slate-400">
          Upload a dataset to see its analysis history.
        </p>
      )}

      {!loading && !error && hasDataset && runs.length === 0 && (
        <p data-testid="history-none" className="mt-3 text-xs text-slate-400">
          No history yet — ask your first question above.
        </p>
      )}

      <ul className="mt-3 space-y-2" data-testid="history-list">
        {runs.map(run => {
          const open = openId === run.run_id
          return (
            <li key={run.run_id} className="rounded-lg border border-slate-200">
              <button
                type="button"
                aria-expanded={open}
                onClick={() => setOpenId(open ? null : run.run_id)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
              >
                <span className="truncate text-xs font-medium text-slate-700">{run.question}</span>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    STATUS_STYLE[run.status] ?? 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {run.status}
                </span>
              </button>

              {open && (
                <div className="space-y-3 border-t border-slate-100 px-3 py-3">
                  {run.answer && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Answer</p>
                      <p className="mt-1 whitespace-pre-wrap text-xs text-slate-700">{run.answer}</p>
                    </div>
                  )}
                  {run.code && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Generated code</p>
                      <pre className="mt-1 overflow-x-auto rounded-md bg-slate-800 p-3 text-[11px] leading-relaxed text-slate-100">
                        <code>{run.code}</code>
                      </pre>
                    </div>
                  )}
                  {run.result_text && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Result</p>
                      <pre className="mt-1 overflow-x-auto rounded-md bg-slate-50 p-2 text-[11px] text-slate-600">
                        {run.result_text}
                      </pre>
                    </div>
                  )}
                  <p className="text-[10px] text-slate-400">{formatTime(run.created_at)}</p>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}
