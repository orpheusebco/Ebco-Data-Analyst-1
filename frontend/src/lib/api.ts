// API client for the data-analysis agent.
//
// The frontend is served at :8001/app/ and the API lives at the origin root
// (:8001) — so all paths below are root-absolute ("/datasets", not
// "/app/datasets"). Responses use the { data, error } envelope for JSON
// endpoints; POST /ask is a text/event-stream consumed via a fetch stream
// reader (EventSource cannot POST a body).

export type DatasetKind = 'csv' | 'xlsx'

export interface ProfileColumn {
  name: string
  dtype: string
  null_count: number
  null_pct: number
  distinct_count: number
  min: string | number | null
  max: string | number | null
  sample_values: string[]
}

export interface QualityFlag {
  type: string
  severity: 'warning' | 'info'
  message: string
  columns: string[]
}

export interface DatasetProfile {
  row_count: number
  column_count: number
  columns: ProfileColumn[]
  quality_flags: QualityFlag[]
}

export interface Dataset {
  dataset_id: string
  name: string
  kind: DatasetKind
  row_count: number
  column_count: number
  profile?: DatasetProfile | null
}

export interface Run {
  run_id: string
  question: string
  code: string | null
  result_text: string | null
  answer: string | null
  status: string
  created_at: string
}

export interface PinnedItem {
  id: string
  run_id: string
  title: string
  chart_spec: unknown | null
  answer: string | null
  position: number
  created_at: string
}

// A parsed SSE event from POST /ask.
export type AskEvent =
  | { type: 'status'; phase: string }
  | { type: 'token'; text: string }
  | { type: 'clarify'; question: string }
  | { type: 'done'; run_id: string; status: string }
  | { type: 'error'; message: string }
  | { type: 'chart'; spec: unknown }
  | { type: 'followups'; items: string[] }
  | { type: 'unknown'; event: string; data: unknown }

interface Envelope<T> {
  data: T | null
  error: { message: string } | string | null
}

function envelopeError(env: Envelope<unknown> | undefined, status: number): string {
  if (env?.error) {
    return typeof env.error === 'string' ? env.error : env.error.message
  }
  return `Request failed (${status})`
}

/**
 * Upload a CSV or Excel file and register it as a dataset. For Excel workbooks
 * a specific `sheet` name may be supplied (obtained from `fetchExcelSheets`).
 */
export async function uploadDataset(file: File, sheet?: string): Promise<Dataset> {
  const form = new FormData()
  form.append('file', file)
  if (sheet) form.append('sheet', sheet)
  const res = await fetch('/datasets', { method: 'POST', body: form })
  let env: Envelope<Dataset> | undefined
  try {
    env = (await res.json()) as Envelope<Dataset>
  } catch {
    throw new Error(`Upload failed (${res.status})`)
  }
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data
}

/**
 * Inspect an Excel workbook and return its sheet names, so the user can pick
 * which sheet to load. CSV files never call this — they upload in one step.
 */
export async function fetchExcelSheets(file: File): Promise<string[]> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/datasets/excel/sheets', { method: 'POST', body: form })
  let env: Envelope<{ sheets: string[] }> | undefined
  try {
    env = (await res.json()) as Envelope<{ sheets: string[] }>
  } catch {
    throw new Error(`Could not read workbook (${res.status})`)
  }
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data.sheets
}

/** List all loaded datasets. */
export async function listDatasets(): Promise<Dataset[]> {
  const res = await fetch('/datasets')
  const env = (await res.json()) as Envelope<{ datasets: Dataset[] }>
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data.datasets
}

/** Per-dataset run history. */
export async function listRuns(datasetId: string): Promise<Run[]> {
  const res = await fetch(`/datasets/${encodeURIComponent(datasetId)}/runs`)
  const env = (await res.json()) as Envelope<{ runs: Run[] }>
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data.runs
}

/** All pinned dashboard items, in display order. */
export async function fetchDashboard(): Promise<PinnedItem[]> {
  const res = await fetch('/dashboard')
  const env = (await res.json()) as Envelope<{ items: PinnedItem[] }>
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data.items
}

/** Pin a completed run's answer/chart to the curated dashboard. */
export async function pinRun(runId: string, title: string): Promise<PinnedItem> {
  const res = await fetch(`/runs/${encodeURIComponent(runId)}/pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  let env: Envelope<PinnedItem> | undefined
  try {
    env = (await res.json()) as Envelope<PinnedItem>
  } catch {
    throw new Error(`Pin failed (${res.status})`)
  }
  if (!res.ok || !env.data) throw new Error(envelopeError(env, res.status))
  return env.data
}

/** Remove a pinned item from the dashboard. */
export async function unpinItem(itemId: string): Promise<void> {
  const res = await fetch(`/dashboard/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
  if (!res.ok) {
    let message = `Unpin failed (${res.status})`
    try {
      const env = (await res.json()) as Envelope<unknown>
      message = envelopeError(env, res.status)
    } catch {
      /* keep default */
    }
    throw new Error(message)
  }
}

/**
 * Export a run's cleaned CSV or formatted report and trigger a browser
 * download. Reads the filename from Content-Disposition when present.
 */
export async function exportRun(runId: string, format: 'csv' | 'report'): Promise<void> {
  const res = await fetch(`/runs/${encodeURIComponent(runId)}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ format }),
  })
  if (!res.ok) {
    let message = `Export failed (${res.status})`
    try {
      const env = (await res.json()) as Envelope<unknown>
      message = envelopeError(env, res.status)
    } catch {
      /* keep default */
    }
    throw new Error(message)
  }
  const blob = await res.blob()
  let filename = `${runId}.${format === 'csv' ? 'csv' : 'md'}`
  const disposition = res.headers.get('Content-Disposition')
  if (disposition) {
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
    if (match) filename = decodeURIComponent(match[1])
  }
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

/**
 * Ask a question against one or more datasets. Streams parsed SSE events to
 * `onEvent` as they arrive. Resolves when the stream closes.
 */
export async function ask(
  datasetIds: string[],
  question: string,
  onEvent: (ev: AskEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_ids: datasetIds, question }),
    signal,
  })

  if (!res.ok || !res.body) {
    // Non-stream error (e.g. 400 unknown dataset) — try to surface the message.
    let message = `Request failed (${res.status})`
    try {
      const env = (await res.json()) as Envelope<unknown>
      message = envelopeError(env, res.status)
    } catch {
      /* keep default */
    }
    onEvent({ type: 'error', message })
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE frames are separated by a blank line.
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const ev = parseFrame(frame)
      if (ev) onEvent(ev)
    }
  }
  // Flush any trailing frame without a terminating blank line.
  const tail = parseFrame(buffer)
  if (tail) onEvent(tail)
}

function parseFrame(frame: string): AskEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const rawLine of frame.split('\n')) {
    const line = rawLine.replace(/\r$/, '')
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }
  if (dataLines.length === 0) return null

  let payload: Record<string, unknown> = {}
  try {
    payload = JSON.parse(dataLines.join('\n'))
  } catch {
    payload = { text: dataLines.join('\n') }
  }

  switch (event) {
    case 'status':
      return { type: 'status', phase: String(payload.phase ?? '') }
    case 'token':
      return { type: 'token', text: String(payload.text ?? '') }
    case 'clarify':
      return { type: 'clarify', question: String(payload.question ?? '') }
    case 'done':
      return {
        type: 'done',
        run_id: String(payload.run_id ?? ''),
        status: String(payload.status ?? ''),
      }
    case 'error':
      return { type: 'error', message: String(payload.message ?? 'Unknown error') }
    case 'chart':
      return { type: 'chart', spec: payload.spec ?? payload }
    case 'followups': {
      const raw = payload.items
      const items = Array.isArray(raw) ? raw.map(String) : []
      return { type: 'followups', items }
    }
    default:
      return { type: 'unknown', event, data: payload }
  }
}
