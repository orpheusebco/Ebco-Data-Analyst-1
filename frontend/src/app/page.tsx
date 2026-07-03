'use client'

import { useCallback, useEffect, useState } from 'react'
import type { Dataset, Run } from '@/lib/api'
import { listRuns } from '@/lib/api'
import UploadPanel from '@/components/UploadPanel'
import ChatPanel from '@/components/ChatPanel'
import HistoryPanel from '@/components/HistoryPanel'
import ProfilePanel from '@/components/ProfilePanel'
import StubCard from '@/components/StubCard'

const STUBS = [
  { title: 'Excel upload', description: 'Load .xlsx workbooks with a sheet picker.', phase: 'Phase 3', icon: '📈' },
  { title: 'Multi-file compare', description: 'Load several datasets and ask cross-dataset questions.', phase: 'Phase 3', icon: '🔀' },
  { title: 'Pinnable dashboard', description: 'Pin answers and charts to a curated, persistent dashboard.', phase: 'Phase 3', icon: '📌' },
  { title: 'Exports', description: 'Download cleaned CSVs and formatted reports.', phase: 'Phase 3', icon: '⬇️' },
]

export default function Home() {
  const [active, setActive] = useState<Dataset | null>(null)
  const [runs, setRuns] = useState<Run[]>([])
  const [runsLoading, setRunsLoading] = useState(false)
  const [runsError, setRunsError] = useState<string | null>(null)

  const refreshRuns = useCallback(async (datasetId: string) => {
    setRunsLoading(true)
    setRunsError(null)
    try {
      setRuns(await listRuns(datasetId))
    } catch (e) {
      setRunsError(e instanceof Error ? e.message : 'Could not load history.')
    } finally {
      setRunsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (active) void refreshRuns(active.dataset_id)
    else setRuns([])
  }, [active, refreshRuns])

  const handleUploaded = (ds: Dataset) => {
    setActive(ds)
    setRuns([])
  }

  const handleRunComplete = () => {
    if (active) void refreshRuns(active.dataset_id)
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-6 lg:px-8">
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <span aria-hidden className="text-2xl">🧮</span>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Data Analysis Agent</h1>
            <p className="text-sm text-slate-500">
              Upload a CSV and ask questions in plain language — the agent writes, runs and explains the pandas.
            </p>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[360px_minmax(0,1fr)_320px]">
        {/* Left column: upload + history */}
        <div className="space-y-6">
          <UploadPanel active={active} onUploaded={handleUploaded} />
          {active && <ProfilePanel profile={active.profile} />}
          <HistoryPanel runs={runs} loading={runsLoading} error={runsError} hasDataset={!!active} />
        </div>

        {/* Center column: chat */}
        <div className="min-h-[70vh] lg:h-[calc(100vh-8rem)]">
          <ChatPanel active={active} onRunComplete={handleRunComplete} />
        </div>

        {/* Right column: the product vision as labelled stubs */}
        <aside className="lg:col-span-2 xl:col-span-1">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-800">Coming soon</h2>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                Roadmap
              </span>
            </div>
            <p className="mb-4 text-xs text-slate-400">
              These are part of the vision but not yet functional. They are disabled placeholders, not bugs.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
              {STUBS.map(s => (
                <StubCard key={s.title} {...s} />
              ))}
            </div>
          </div>
        </aside>
      </div>
    </main>
  )
}
