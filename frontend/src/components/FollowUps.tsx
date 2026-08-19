'use client'

interface FollowUpsProps {
  items: string[]
  onSelect: (question: string) => void
  disabled?: boolean
}

export default function FollowUps({ items, onSelect, disabled }: FollowUpsProps) {
  if (!items || items.length === 0) return null

  return (
    <div data-testid="followups" className="mt-3">
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400">
        Ask a follow-up
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <button
            key={`${i}-${item}`}
            type="button"
            data-testid="followup-chip"
            disabled={disabled}
            onClick={() => onSelect(item)}
            className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-50"
          >
            {item}
          </button>
        ))}
      </div>
    </div>
  )
}
