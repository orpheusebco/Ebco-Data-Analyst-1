'use client'

import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AskEvent, Dataset } from '@/lib/api'
import { ask } from '@/lib/api'
import ChartView from '@/components/ChartView'
import FollowUps from '@/components/FollowUps'

interface Turn {
  id: string
  question: string
  answer: string
  clarify: string | null
  error: string | null
  status: string // '' when settled
  chartSpec: unknown | null
  followups: string[]
}

const PHASE_LABEL: Record<string, string> = {
  planning: 'Planning an approach…',
  writing_code: 'Writing pandas code…',
  executing: 'Running the analysis…',
  inspecting: 'Inspecting the result…',
  retrying: 'First attempt failed — retrying a different way…',
}

interface ChatPanelProps {
  active: Dataset | null
  onRunComplete: () => void
}

export default function ChatPanel({ active, onRunComplete }: ChatPanelProps) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [phase, setPhase] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, phase])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await runQuestion(input.trim())
  }

  async function runQuestion(raw: string) {
    const question = raw.trim()
    if (!question || !active || streaming) return

    const id = `${Date.now()}`
    setTurns(prev => [
      ...prev,
      { id, question, answer: '', clarify: null, error: null, status: 'planning', chartSpec: null, followups: [] },
    ])
    setInput('')
    setStreaming(true)
    setPhase('planning')

    const update = (patch: Partial<Turn>) =>
      setTurns(prev => prev.map(t => (t.id === id ? { ...t, ...patch } : t)))

    const onEvent = (ev: AskEvent) => {
      switch (ev.type) {
        case 'status':
          setPhase(ev.phase)
          update({ status: ev.phase })
          break
        case 'token':
          setTurns(prev => prev.map(t => (t.id === id ? { ...t, answer: t.answer + ev.text } : t)))
          break
        case 'clarify':
          update({ clarify: ev.question, status: '' })
          break
        case 'chart':
          update({ chartSpec: ev.spec })
          break
        case 'followups':
          update({ followups: ev.items })
          break
        case 'error':
          update({ error: ev.message, status: '' })
          break
        case 'done':
          update({ status: '' })
          break
        default:
          break
      }
    }

    try {
      await ask([active.dataset_id], question, onEvent)
    } catch (err) {
      update({ error: err instanceof Error ? err.message : 'The request failed.', status: '' })
    } finally {
      setStreaming(false)
      setPhase(null)
      onRunComplete()
    }
  }

  return (
    <section aria-labelledby="chat-heading" className="flex h-full min-h-0 flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-3">
        <h2 id="chat-heading" className="text-sm font-semibold text-slate-800">
          Ask your data
        </h2>
        <p className="text-xs text-slate-400">
          {active ? `Analysing ${active.name}` : 'Upload a CSV to start asking questions.'}
        </p>
      </div>

      <div ref={scrollRef} data-testid="transcript" className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {turns.length === 0 && !streaming && (
          <div data-testid="chat-empty" className="flex h-full flex-col items-center justify-center text-center">
            <span aria-hidden className="text-3xl">💬</span>
            <p className="mt-3 text-sm font-medium text-slate-600">
              {active ? 'Ask a question about your data' : 'Upload a CSV to begin'}
            </p>
            <p className="mt-1 max-w-xs text-xs text-slate-400">
              e.g. &ldquo;What is the average revenue grouped by region?&rdquo; The agent writes and runs
              the pandas for you, then explains the numbers.
            </p>
          </div>
        )}

        {turns.map(turn => (
          <div key={turn.id} className="space-y-2">
            <div className="flex justify-end">
              <p
                data-testid="user-message"
                className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white"
              >
                {turn.question}
              </p>
            </div>

            <div className="flex justify-start">
              <div
                data-testid="assistant-message"
                className="max-w-[92%] rounded-2xl rounded-bl-sm border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800"
              >
                {turn.status && !turn.answer ? (
                  <div data-testid="agent-spinner" className="flex items-center gap-2 text-indigo-600">
                    <Spinner />
                    <span>{PHASE_LABEL[turn.status] ?? 'Working…'}</span>
                  </div>
                ) : (
                  <>
                    {turn.answer && (
                      <div className="prose prose-sm max-w-none prose-pre:bg-slate-800 prose-pre:text-slate-100">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.answer}</ReactMarkdown>
                      </div>
                    )}
                    {turn.status && turn.answer && (
                      <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-indigo-400 align-middle" aria-hidden />
                    )}
                    {turn.chartSpec != null && <ChartView spec={turn.chartSpec} />}
                    {turn.followups.length > 0 && (
                      <FollowUps items={turn.followups} onSelect={q => void runQuestion(q)} disabled={streaming} />
                    )}
                    {turn.clarify && (
                      <div
                        data-testid="clarify"
                        className="mt-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800"
                      >
                        <span className="font-semibold">Needs clarification: </span>
                        {turn.clarify}
                      </div>
                    )}
                    {turn.error && (
                      <div
                        role="alert"
                        data-testid="agent-error"
                        className="mt-1 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-700"
                      >
                        {turn.error}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-slate-100 p-3">
        {phase && (
          <p data-testid="phase-label" className="mb-2 px-1 text-xs font-medium text-indigo-600">
            {PHASE_LABEL[phase] ?? 'Working…'}
          </p>
        )}
        <div className="flex items-end gap-2">
          <label htmlFor="question-input" className="sr-only">
            Your question
          </label>
          <textarea
            id="question-input"
            data-testid="question-input"
            rows={1}
            value={input}
            disabled={!active || streaming}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void handleSubmit(e as unknown as React.FormEvent)
              }
            }}
            placeholder={active ? 'Ask a question…' : 'Upload a CSV first'}
            className="max-h-32 min-h-[42px] flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50"
          />
          <button
            type="submit"
            data-testid="ask-button"
            disabled={!active || streaming || !input.trim()}
            className="shrink-0 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
          >
            {streaming ? 'Thinking…' : 'Ask'}
          </button>
        </div>
      </form>
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
