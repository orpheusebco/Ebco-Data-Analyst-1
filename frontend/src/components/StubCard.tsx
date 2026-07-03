// A clearly-labelled, NON-FUNCTIONAL placeholder for a feature that ships in a
// later phase. Visibly disabled and badged so it can never be mistaken for a
// bug — it announces itself as "coming soon".

interface StubCardProps {
  title: string
  description: string
  phase: string
  icon: string
}

export default function StubCard({ title, description, phase, icon }: StubCardProps) {
  return (
    <div
      aria-disabled="true"
      data-testid="stub-card"
      className="relative select-none rounded-xl border border-dashed border-slate-300 bg-slate-50/70 p-4 opacity-70"
    >
      <span
        data-testid="coming-soon-badge"
        className="absolute right-3 top-3 rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500"
      >
        {phase} · Coming soon
      </span>
      <div className="flex items-start gap-3">
        <span aria-hidden className="text-xl leading-none">
          {icon}
        </span>
        <div className="pr-24">
          <h3 className="text-sm font-semibold text-slate-600">{title}</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{description}</p>
        </div>
      </div>
    </div>
  )
}
