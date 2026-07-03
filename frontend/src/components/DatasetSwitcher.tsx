'use client'

import type { Dataset } from '@/lib/api'

interface DatasetSwitcherProps {
  datasets: Dataset[]
  selectedIds: string[]
  onToggle: (id: string) => void
  loading: boolean
  error: string | null
}

// Lists every loaded dataset with a checkbox to include it in the analysis
// scope. Selecting 2+ lets the user ask cross-dataset comparison questions.
export default function DatasetSwitcher({
  datasets,
  selectedIds,
  onToggle,
  loading,
  error,
}: DatasetSwitcherProps) {
  const selectedCount = selectedIds.length

  return (
    <section
      data-testid="dataset-switcher"
      aria-labelledby="switcher-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-baseline justify-between">
        <h2 id="switcher-heading" className="text-sm font-semibold text-slate-800">
          Loaded datasets
        </h2>
        {datasets.length > 0 && (
          <span
            data-testid="selected-count"
            className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700"
          >
            {selectedCount} selected
          </span>
        )}
      </div>

      {loading && (
        <p data-testid="switcher-loading" className="mt-3 text-xs text-slate-400">
          Loading datasets…
        </p>
      )}

      {error && (
        <p role="alert" data-testid="switcher-error" className="mt-3 text-xs text-red-600">
          {error}
        </p>
      )}

      {!loading && !error && datasets.length === 0 && (
        <p data-testid="switcher-empty" className="mt-3 text-xs text-slate-400">
          No datasets loaded yet — upload one above. Load several to compare them.
        </p>
      )}

      {datasets.length > 0 && (
        <>
          <ul className="mt-3 space-y-2" data-testid="dataset-list">
            {datasets.map(ds => {
              const checked = selectedIds.includes(ds.dataset_id)
              return (
                <li key={ds.dataset_id}>
                  <label
                    data-testid="dataset-option"
                    data-selected={checked}
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 transition ${
                      checked
                        ? 'border-indigo-300 bg-indigo-50'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      data-testid="dataset-checkbox"
                      checked={checked}
                      onChange={() => onToggle(ds.dataset_id)}
                      className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-xs font-medium text-slate-700">{ds.name}</span>
                        <span className="shrink-0 rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-slate-500">
                          {ds.kind}
                        </span>
                      </span>
                      <span className="mt-0.5 block text-[10px] text-slate-400 tabular-nums">
                        {ds.row_count.toLocaleString()} rows · {ds.column_count.toLocaleString()} cols
                      </span>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          <p className="mt-2 text-[11px] text-slate-400">
            {selectedCount >= 2
              ? 'Cross-dataset mode — questions run against all selected datasets.'
              : 'Select 2+ datasets to ask cross-dataset comparison questions.'}
          </p>
        </>
      )}
    </section>
  )
}
