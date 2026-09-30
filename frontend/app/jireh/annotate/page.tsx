'use client'

import { useEffect, useState } from 'react'
import { Loader2, Star, CheckCircle2, AlertTriangle, RefreshCw, ClipboardList } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import { dukeApi, DukeApiError, type DukeTask } from '@/lib/duke-api'
import { EmptyState, LoadingRow, PageHeader } from '../../components/ui'
import MarkdownMessage from '../../components/duke/MarkdownMessage'
import { parseResponse } from '../../components/duke/parseResponse'
import { getAgent } from '../../components/duke/agents'

export default function AdminAnnotatePage() {
  const [tasks, setTasks] = useState<DukeTask[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [selected, setSelected] = useState<DukeTask | null>(null)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const load = async () => {
    setListError(null)
    try {
      const data = await dukeApi.listTasks(50)
      setTasks(data)
    } catch (err) {
      setListError(err instanceof DukeApiError ? err.message : 'Could not reach the Duke backend.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const selectTask = (task: DukeTask) => {
    setSelected(task)
    setRating(0)
    setComment('')
    setNotice(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected || rating === 0) return

    setSubmitting(true)
    setNotice(null)
    try {
      await dukeApi.submitFeedback({
        request_id: selected.id,
        rating,
        comment,
        agent_name: selected.agent_name,
      })
      setNotice({ type: 'success', message: 'Feedback submitted - it feeds DUKE’s continual learning pipeline.' })
      setRating(0)
      setComment('')
    } catch (err) {
      setNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Failed to submit feedback.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AdminShell>
      <PageHeader
        eyebrow="JIREH · Model"
        title="Annotate"
        description="Review recent queries and rate or correct DUKE's responses. Low ratings are excluded from future training."
        actions={
          <button type="button" onClick={load} className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4" aria-hidden="true" /> Refresh
          </button>
        }
      />

      {listError && (
        <div role="alert" className="alert mb-6 alert-error">
          {listError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <nav aria-label="Recent queries" className="surface h-fit max-h-[36rem] overflow-y-auto p-3 lg:col-span-1">
          <p className="px-3 pt-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">Recent queries</p>
          {listError && !tasks ? (
            <p className="px-3 pb-2 text-xs text-gray-500">Unavailable - see the error above.</p>
          ) : !tasks ? (
            <LoadingRow label="Loading queries…" className="px-3" />
          ) : tasks.length === 0 ? (
            <p className="px-3 pb-2 text-sm text-gray-400">No queries yet.</p>
          ) : (
            <ul className="space-y-0.5">
              {tasks.map((task) => {
                const active = selected?.id === task.id
                return (
                  <li key={task.id}>
                    <button
                      type="button"
                      onClick={() => selectTask(task)}
                      aria-current={active ? 'true' : undefined}
                      className={`w-full rounded-lg px-3 py-2.5 text-left transition-colors cursor-pointer ${
                        active ? 'bg-white/[0.07]' : 'hover:bg-white/[0.04]'
                      }`}
                    >
                      <span className="mb-1 block text-[11px] font-medium text-gold-400">{getAgent(task.agent_name).name}</span>
                      <span className={`line-clamp-2 block text-xs ${active ? 'text-white' : 'text-gray-300'}`}>{task.description}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </nav>

        <GlassCard className="lg:col-span-2">
          {!selected ? (
            <EmptyState
              icon={ClipboardList}
              title="No query selected"
              description="Pick a recent query on the left to read DUKE's answer, rate it, and correct it if needed."
            />
          ) : (
            <div className="space-y-6">
              <div>
                <h2 className="eyebrow mb-2 text-gray-500">Query</h2>
                <p className="text-sm text-white">{selected.description}</p>
              </div>
              <div>
                <h2 className="eyebrow mb-2 text-gray-500">Response</h2>
                <div className="surface-inset p-4">
                  {selected.result ? (
                    <>
                      <MarkdownMessage content={parseResponse(selected.result).body} />
                      {parseResponse(selected.result).sources.length > 0 && (
                        <p className="mt-3 border-t border-white/5 pt-3 text-xs text-gray-500">
                          Sources: {parseResponse(selected.result).sources.join(' · ')}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-gray-500">No response recorded.</p>
                  )}
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4 border-t border-white/[0.07] pt-5">
                {notice && (
                  <div
                    role="alert"
                    className={`alert ${
                      notice.type === 'success' ? 'alert-success' : 'alert-error'
                    }`}
                  >
                    {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                    {notice.message}
                  </div>
                )}

                <div>
                  <label className="label">Rating</label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setRating(n)}
                        aria-label={`Rate ${n} out of 5`}
                        className="cursor-pointer"
                      >
                        <Star className={`w-6 h-6 transition-colors ${n <= rating ? 'fill-gold-500 text-gold-500' : 'text-gray-600'}`} />
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="comment" className="label">
                    Correction or comment (optional)
                  </label>
                  <textarea
                    id="comment"
                    rows={4}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="What should the response have said instead?"
                    className="input w-full resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={rating === 0 || submitting}
                  className="btn btn-primary btn-lg"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Submit feedback'}
                </button>
              </form>
            </div>
          )}
        </GlassCard>
      </div>
    </AdminShell>
  )
}
