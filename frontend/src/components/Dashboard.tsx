'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { PinnedItem } from '@/lib/api'
import ChartView from '@/components/ChartView'

interface DashboardProps {
  items: PinnedItem[]
  loading: boolean
  error: string | null
  onUnpin: (itemId: string) => void
}

// The curated main view: pinned answers and charts, persisted in the DB, shown
// as reorderable-in-spirit tiles. Survives reloads because it is fetched fresh.
export default function Dashboard({ items, loading, error, onUnpin }: DashboardProps) {
  const [removing, setRemoving] = useState<string | null>(null)

  async function handleUnpin(id: string) {
    setRemoving(id)
    try {
      await onUnpin(id)
    } finally {
      setRemoving(null)
    }
  }

  return (
    <section
      data-testid="dashboard"
      aria-labelledby="dashboard-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span aria-hidden className="text-lg">📌</span>
          <h2 id="dashboard-heading" className="text-sm font-semibold text-slate-800">
            Dashboard
          </h2>
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
          {items.length} pinned
        </span>
      </div>

      {loading && (
        <p data-testid="dashboard-loading" className="text-xs text-slate-400">
          Loading pinned items…
        </p>
      )}

      {error && (
        <p role="alert" data-testid="dashboard-error" className="text-xs text-red-600">
          {error}
        </p>
      )}

      {!loading && !error && items.length === 0 && (
        <div
          data-testid="dashboard-empty"
          className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center"
        >
          <p className="text-sm font-medium text-slate-600">Your dashboard is empty</p>
          <p className="mt-1 text-xs text-slate-400">
            Pin an answer or chart from the chat to curate it here — it persists across reloads.
          </p>
        </div>
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map(item => (
            <article
              key={item.id}
              data-testid="dashboard-tile"
              className="flex flex-col rounded-xl border border-slate-200 bg-slate-50/60 p-4"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="min-w-0 flex-1 truncate text-xs font-semibold text-slate-700">
                  {item.title}
                </h3>
                <button
                  type="button"
                  data-testid="unpin-button"
                  disabled={removing === item.id}
                  onClick={() => void handleUnpin(item.id)}
                  className="shrink-0 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-500 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                >
                  {removing === item.id ? 'Removing…' : 'Unpin'}
                </button>
              </div>
              {item.answer && (
                <div className="prose prose-sm max-w-none text-slate-700 prose-pre:bg-slate-800 prose-pre:text-slate-100">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.answer}</ReactMarkdown>
                </div>
              )}
              {item.chart_spec != null && <ChartView spec={item.chart_spec} />}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
