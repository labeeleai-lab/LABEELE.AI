'use client'

import { useEffect, useState } from 'react'
import { Loader2, Star, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import { dukeApi, DukeApiError, type DukeTask } from '@/lib/duke-api'

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
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-3xl font-bold text-white">Annotate</h1>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gold-500 transition-colors cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>
      <p className="text-gray-400 mb-8">Review recent queries and rate or correct DUKE&apos;s responses.</p>

      {listError && (
        <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
          {listError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-1 h-fit max-h-[36rem] overflow-y-auto">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">Recent queries</h2>
          {!tasks ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : tasks.length === 0 ? (
            <p className="text-gray-400 text-sm">No queries yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {tasks.map((task) => (
                <li key={task.id}>
                  <button
                    onClick={() => selectTask(task)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer ${
                      selected?.id === task.id
                        ? 'bg-gold-500/15 text-gold-500 border border-gold-500/30'
                        : 'text-gray-300 hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <p className="text-xs text-gold-500/80 font-medium mb-1">{task.agent_name}</p>
                    <p className="line-clamp-2 text-xs">{task.description}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <GlassCard className="lg:col-span-2">
          {!selected ? (
            <p className="text-gray-400 text-sm">Select a query to review.</p>
          ) : (
            <div className="space-y-6">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Query</h2>
                <p className="text-white text-sm">{selected.description}</p>
              </div>
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Response</h2>
                <p className="text-gray-300 text-sm whitespace-pre-wrap bg-white/5 border border-gold-500/15 rounded-lg p-4">
                  {selected.result || 'No response recorded.'}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4 pt-2 border-t border-gold-500/10">
                {notice && (
                  <div
                    role="alert"
                    className={`p-3 rounded-lg border text-sm flex items-start gap-2 ${
                      notice.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
                    }`}
                  >
                    {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                    {notice.message}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Rating</label>
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
                  <label htmlFor="comment" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Correction or comment (optional)
                  </label>
                  <textarea
                    id="comment"
                    rows={4}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="What should the response have said instead?"
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={rating === 0 || submitting}
                  className="flex items-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
