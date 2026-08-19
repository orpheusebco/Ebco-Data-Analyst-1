'use client'

import type { DatasetProfile } from '@/lib/api'

interface ProfilePanelProps {
  profile: DatasetProfile | null | undefined
}

function formatCell(value: string | number | null): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

export default function ProfilePanel({ profile }: ProfilePanelProps) {
  if (!profile || !profile.columns || profile.columns.length === 0) {
    return (
      <section
        data-testid="profile-panel"
        aria-labelledby="profile-heading"
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <h2 id="profile-heading" className="text-sm font-semibold text-slate-800">
          Dataset profile
        </h2>
        <p className="mt-2 text-xs text-slate-400">No profile available for this dataset.</p>
      </section>
    )
  }

  const flags = profile.quality_flags ?? []

  return (
    <section
      data-testid="profile-panel"
      aria-labelledby="profile-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-baseline justify-between">
        <h2 id="profile-heading" className="text-sm font-semibold text-slate-800">
          Dataset profile
        </h2>
        <span className="text-[11px] text-slate-400 tabular-nums">
          {profile.row_count.toLocaleString()} rows · {profile.column_count.toLocaleString()} cols
        </span>
      </div>

      {flags.length > 0 && (
        <div data-testid="quality-flags" className="mt-3 flex flex-wrap gap-2">
          {flags.map((flag, i) => (
            <span
              key={`${flag.type}-${i}`}
              data-testid="quality-flag"
              data-severity={flag.severity}
              title={flag.columns.length ? `Columns: ${flag.columns.join(', ')}` : undefined}
              className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                flag.severity === 'warning'
                  ? 'border-amber-200 bg-amber-50 text-amber-700'
                  : 'border-slate-200 bg-slate-50 text-slate-600'
              }`}
            >
              {flag.message}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 max-h-72 overflow-auto rounded-lg border border-slate-100">
        <table className="w-full min-w-[520px] text-left text-[11px] tabular-nums">
          <thead className="sticky top-0 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-2 py-1.5 font-semibold">Column</th>
              <th className="px-2 py-1.5 font-semibold">Type</th>
              <th className="px-2 py-1.5 font-semibold">Nulls</th>
              <th className="px-2 py-1.5 font-semibold">Distinct</th>
              <th className="px-2 py-1.5 font-semibold">Min</th>
              <th className="px-2 py-1.5 font-semibold">Max</th>
              <th className="px-2 py-1.5 font-semibold">Sample</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map(col => (
              <tr key={col.name} data-testid="profile-column" className="border-t border-slate-100">
                <td className="px-2 py-1.5 font-medium text-slate-700">{col.name}</td>
                <td className="px-2 py-1.5 text-slate-500">{col.dtype}</td>
                <td className="px-2 py-1.5 text-slate-500">
                  {col.null_count} ({Math.round(col.null_pct)}%)
                </td>
                <td className="px-2 py-1.5 text-slate-500">{col.distinct_count}</td>
                <td className="px-2 py-1.5 text-slate-500">{formatCell(col.min)}</td>
                <td className="px-2 py-1.5 text-slate-500">{formatCell(col.max)}</td>
                <td className="px-2 py-1.5 text-slate-400">
                  {(col.sample_values ?? []).slice(0, 3).join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
