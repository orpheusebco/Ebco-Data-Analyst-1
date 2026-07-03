'use client'

import { useCallback, useEffect, useState } from 'react'
import type { Dataset, PinnedItem, Run } from '@/lib/api'
import { fetchDashboard, listDatasets, listRuns, unpinItem } from '@/lib/api'
import UploadPanel from '@/components/UploadPanel'
import DatasetSwitcher from '@/components/DatasetSwitcher'
import ChatPanel from '@/components/ChatPanel'
import HistoryPanel from '@/components/HistoryPanel'
import ProfilePanel from '@/components/ProfilePanel'
import Dashboard from '@/components/Dashboard'

export default function Home() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [datasetsLoading, setDatasetsLoading] = useState(false)
  const [datasetsError, setDatasetsError] = useState<string | null>(null)

  const [runs, setRuns] = useState<Run[]>([])
  const [runsLoading, setRunsLoading] = useState(false)
  const [runsError, setRunsError] = useState<string | null>(null)

  const [pinned, setPinned] = useState<PinnedItem[]>([])
  const [pinnedLoading, setPinnedLoading] = useState(false)
  const [pinnedError, setPinnedError] = useState<string | null>(null)

  // The selected datasets, in selection order; the first is the primary that
  // drives the profile + history panels.
  const selected = selectedIds
    .map(id => datasets.find(d => d.dataset_id === id))
    .filter((d): d is Dataset => d != null)
  const primary = selected[0] ?? null

  const refreshDatasets = useCallback(async () => {
    setDatasetsLoading(true)
    setDatasetsError(null)
    try {
      const list = await listDatasets()
      setDatasets(list)
      return list
    } catch (e) {
      setDatasetsError(e instanceof Error ? e.message : 'Could not load datasets.')
      return [] as Dataset[]
    } finally {
      setDatasetsLoading(false)
    }
  }, [])

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

  const refreshDashboard = useCallback(async () => {
    setPinnedLoading(true)
    setPinnedError(null)
    try {
      setPinned(await fetchDashboard())
    } catch (e) {
      setPinnedError(e instanceof Error ? e.message : 'Could not load dashboard.')
    } finally {
      setPinnedLoading(false)
    }
  }, [])

  // Load the dataset list + persisted dashboard once on mount.
  useEffect(() => {
    void (async () => {
      const list = await refreshDatasets()
      if (list.length > 0) setSelectedIds([list[0].dataset_id])
    })()
    void refreshDashboard()
  }, [refreshDatasets, refreshDashboard])

  // Keep history in sync with the primary selected dataset.
  useEffect(() => {
    if (primary) void refreshRuns(primary.dataset_id)
    else setRuns([])
  }, [primary, refreshRuns])

  const handleUploaded = async (ds: Dataset) => {
    await refreshDatasets()
    // Make the freshly uploaded dataset the primary (first-selected) so the
    // profile + history focus on it, while keeping any prior selections in scope.
    setSelectedIds(prev => [ds.dataset_id, ...prev.filter(id => id !== ds.dataset_id)])
  }

  const handleToggle = (id: string) => {
    setSelectedIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]))
  }

  const handleRunComplete = () => {
    if (primary) void refreshRuns(primary.dataset_id)
  }

  const handleUnpin = async (itemId: string) => {
    try {
      await unpinItem(itemId)
      setPinned(prev => prev.filter(p => p.id !== itemId))
    } catch (e) {
      setPinnedError(e instanceof Error ? e.message : 'Could not unpin item.')
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-6 lg:px-8">
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <span aria-hidden className="text-2xl">🧮</span>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Data Analysis Agent</h1>
            <p className="text-sm text-slate-500">
              Upload CSV or Excel files, compare across datasets, and ask questions in plain language —
              the agent writes, runs and explains the pandas.
            </p>
          </div>
        </div>
      </header>

      {/* The curated dashboard is the primary view — persisted pinned answers. */}
      <div className="mb-6">
        <Dashboard items={pinned} loading={pinnedLoading} error={pinnedError} onUnpin={handleUnpin} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        {/* Left column: upload + dataset switcher + profile + history */}
        <div className="space-y-6">
          <UploadPanel active={primary} onUploaded={ds => void handleUploaded(ds)} />
          <DatasetSwitcher
            datasets={datasets}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            loading={datasetsLoading}
            error={datasetsError}
          />
          {primary && <ProfilePanel profile={primary.profile} />}
          <HistoryPanel runs={runs} loading={runsLoading} error={runsError} hasDataset={!!primary} />
        </div>

        {/* Center column: chat */}
        <div className="min-h-[70vh] lg:h-[calc(100vh-8rem)]">
          <ChatPanel datasets={selected} onRunComplete={handleRunComplete} onPinned={() => void refreshDashboard()} />
        </div>
      </div>
    </main>
  )
}
