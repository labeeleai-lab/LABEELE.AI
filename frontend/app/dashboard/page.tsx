'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { History, Sparkles } from 'lucide-react'
import AppShell from '../components/AppShell'
import StatusCard from '../components/StatusCard'
import Composer from '../components/duke/Composer'
import { AGENTS, getAgent } from '../components/duke/agents'
import { parseResponse } from '../components/duke/parseResponse'
import { AgentAvatar, AssistantMessage, ErrorMessage, PendingMessage, UserMessage, type Turn } from '../components/duke/Messages'
import { dukeApi, DukeApiError, type HealthStatus, type ModelStatus, type LearningStatus } from '@/lib/duke-api'
import { listRecentQueries, saveQuery, type AgentQuery } from '@/lib/query-history'

function useBackendStatus() {
  const [health, setHealth] = useState<{ data?: HealthStatus; loading: boolean; error?: string }>({ loading: true })
  const [model, setModel] = useState<{ data?: ModelStatus; loading: boolean; error?: string }>({ loading: true })
  const [learning, setLearning] = useState<{ data?: LearningStatus; loading: boolean; error?: string }>({ loading: true })

  useEffect(() => {
    dukeApi.health().then(
      (data) => setHealth({ data, loading: false }),
      (err) => setHealth({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
    dukeApi.modelStatus().then(
      (data) => setModel({ data, loading: false }),
      (err) => setModel({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
    dukeApi.learningStatus().then(
      (data) => setLearning({ data, loading: false }),
      (err) => setLearning({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
  }, [])

  return { health, model, learning }
}

const readFileAsBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.slice(result.indexOf(',') + 1))
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })

const STARTERS = [
  { agentId: 'duke', text: 'What should a small team prioritize first when hardening a new production API?' },
  { agentId: 'security-expert', text: 'Explain the principle of least privilege with a practical example.' },
  { agentId: 'ml-expert', text: 'How do I tell whether my model is overfitting, and what can I do about it?' },
  { agentId: 'devops-expert', text: 'What is the difference between a canary release and a blue-green deployment?' },
]

let turnSeq = 0
const nextId = () => `t${Date.now()}-${turnSeq++}`

export default function DashboardPage() {
  const { health, model, learning } = useBackendStatus()

  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [history, setHistory] = useState<AgentQuery[]>([])

  const [query, setQuery] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>(AGENTS[0].id)
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [inputNotice, setInputNotice] = useState<string | null>(null)
  const loading = turns.some((t) => t.kind === 'pending')
  const threadEndRef = useRef<HTMLDivElement>(null)

  const refreshHistory = useCallback(async () => {
    setHistory(await listRecentQueries())
  }, [])

  useEffect(() => {
    fetch('/api/auth/me')
      .then((res) => res.json())
      .then((body) => {
        if (body.user) {
          setUserEmail(body.user.email)
          refreshHistory()
        }
      })
  }, [refreshHistory])

  // Keep the newest message in view as the conversation grows
  useEffect(() => {
    if (!turns.length) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    threadEndRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'nearest' })
  }, [turns])

  const ask = async (text: string, agentId: string, file: File | null) => {
    if (!text.trim() || loading) return
    const pendingId = nextId()
    const startedAt = Date.now()
    setTurns((prev) => [
      ...prev,
      { kind: 'user', id: nextId(), agentId, text, attachment: file?.name, at: new Date() },
      { kind: 'pending', id: pendingId, agentId, startedAt },
    ])
    setQuery('')
    setAttachedFile(null)
    setInputNotice(null)

    let finished: Turn
    try {
      let attachment_base64: string | undefined
      let attachment_name: string | undefined
      if (file) {
        attachment_base64 = await readFileAsBase64(file)
        attachment_name = file.name
      }

      const data = await dukeApi.submitTask({
        description: text,
        complexity: 5,
        target_agent: agentId,
        buyer_id: userEmail ?? 'dashboard-user',
        attachment_base64,
        attachment_name,
      })

      const response = data.response || 'No response received'
      finished = {
        kind: 'assistant',
        id: pendingId,
        agentId,
        parsed: parseResponse(response, data.response_source, data.sources),
        at: new Date(),
        seconds: (Date.now() - startedAt) / 1000,
      }

      if (userEmail) {
        saveQuery(agentId, text, response).then(refreshHistory)
      }
    } catch (err) {
      finished = {
        kind: 'error',
        id: pendingId,
        agentId,
        message: err instanceof DukeApiError ? err.message : 'Query failed',
        retryText: text,
      }
    }
    setTurns((prev) => prev.map((t) => (t.id === pendingId ? finished : t)))
  }

  const statusOnline = health.data?.status === 'ok'

  return (
    <AppShell>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-1 text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400">{userEmail ? `Signed in as ${userEmail}` : 'Deploy a specialist agent for any task.'}</p>
        </div>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatusCard
          label="Backend"
          loading={health.loading}
          error={health.error}
          value={statusOnline ? 'Online' : health.data?.status}
          tone={statusOnline ? 'good' : 'warn'}
          detail={health.data?.service}
        />
        <StatusCard
          label="Model"
          loading={model.loading}
          error={model.error}
          value={model.data?.status === 'ready' ? 'Ready' : 'Training'}
          tone={model.data?.status === 'ready' ? 'good' : 'warn'}
          detail={model.data?.version ? `v${model.data.version}` : undefined}
        />
        <StatusCard
          label="Specialists online"
          loading={learning.loading}
          error={learning.error}
          value={learning.data ? String(learning.data.agent_personas?.length ?? 0) : undefined}
          detail={learning.data ? `${learning.data.total_inferences ?? 0} total queries` : undefined}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="min-w-0 space-y-4 lg:col-span-2" aria-label="DUKE workspace">
          <div className="glass-panel overflow-hidden">
            <div className="flex items-center gap-3 border-b border-white/5 px-4 py-3 sm:px-5">
              <span className="relative flex h-2 w-2" aria-hidden="true">
                {statusOnline && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/60" />}
                <span className={`relative inline-flex h-2 w-2 rounded-full ${statusOnline ? 'bg-emerald-400' : health.loading ? 'bg-gray-500' : 'bg-amber-400'}`} />
              </span>
              <h2 className="text-sm font-semibold text-white">DUKE workspace</h2>
              <span className="text-xs text-gray-500">
                {health.loading ? 'Checking status…' : statusOnline ? 'Online' : 'Backend unavailable'}
              </span>
              {turns.length > 0 && !loading && (
                <button
                  type="button"
                  onClick={() => setTurns([])}
                  className="ml-auto rounded-md px-2 py-1 text-xs text-gray-400 transition-colors hover:bg-white/5 hover:text-gold-400 cursor-pointer"
                >
                  New conversation
                </button>
              )}
            </div>

            <div className="space-y-5 px-3 py-5 sm:px-5" aria-live="polite" aria-relevant="additions">
              {turns.length === 0 ? (
                <div className="px-1 py-6 text-center sm:py-10">
                  <span className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl border border-gold-500/40 bg-gradient-to-br from-gold-500/25 to-gold-500/5 text-gold-400">
                    <Sparkles className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <p className="text-lg font-semibold text-white">What can DUKE help you with?</p>
                  <p className="mx-auto mt-1 max-w-md text-sm text-gray-400">
                    Ask DUKE to coordinate across every specialist, or pick one directly below. Answers cite the knowledge-base
                    sources they draw on.
                  </p>
                  <div className="mx-auto mt-6 grid max-w-2xl grid-cols-1 gap-2.5 text-left sm:grid-cols-2">
                    {STARTERS.map((s) => {
                      const agent = getAgent(s.agentId)
                      return (
                        <button
                          key={s.text}
                          type="button"
                          onClick={() => {
                            setSelectedAgent(s.agentId)
                            setQuery(s.text)
                          }}
                          className="glass-raised group flex items-start gap-3 p-3 text-left transition-colors hover:border-gold-500/40 cursor-pointer"
                        >
                          <AgentAvatar agent={agent} size="sm" />
                          <span className="min-w-0">
                            <span className="block text-[11px] font-medium uppercase tracking-wider text-gray-500 group-hover:text-gold-400">
                              {agent.name}
                            </span>
                            <span className="mt-0.5 block text-sm text-gray-200">{s.text}</span>
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              ) : (
                turns.map((turn) => {
                  switch (turn.kind) {
                    case 'user':
                      return <UserMessage key={turn.id} turn={turn} />
                    case 'pending':
                      return <PendingMessage key={turn.id} turn={turn} />
                    case 'assistant':
                      return <AssistantMessage key={turn.id} turn={turn} />
                    case 'error':
                      return (
                        <ErrorMessage
                          key={turn.id}
                          turn={turn}
                          disabled={loading}
                          onRetry={() => ask(turn.retryText, turn.agentId, null)}
                        />
                      )
                  }
                })
              )}
              <div ref={threadEndRef} />
            </div>
          </div>

          {inputNotice && (
            <p role="alert" className="glass-raised border-amber-400/30 px-4 py-2.5 text-sm text-amber-100">
              {inputNotice}
            </p>
          )}

          <Composer
            query={query}
            onQueryChange={setQuery}
            selectedAgent={selectedAgent}
            onAgentChange={setSelectedAgent}
            attachedFile={attachedFile}
            onAttach={(f) => {
              setAttachedFile(f)
              setInputNotice(null)
            }}
            onAttachError={setInputNotice}
            onSubmit={() => ask(query, selectedAgent, attachedFile)}
            loading={loading}
          />
        </section>

        <aside className="glass-panel h-fit p-4 sm:p-5" aria-label="Recent queries">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
            <History className="h-4 w-4 text-gold-500" aria-hidden="true" /> Recent queries
          </h2>
          <div className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
            {history.length === 0 ? (
              <p className="text-sm text-gray-400">No queries yet - ask something to get started.</p>
            ) : (
              history.map((item) => {
                const agent = getAgent(item.agent_id)
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setQuery(item.query)
                      setSelectedAgent(item.agent_id)
                    }}
                    className="glass-raised flex w-full items-start gap-2.5 p-3 text-left transition-colors hover:border-gold-500/40 cursor-pointer"
                  >
                    <AgentAvatar agent={agent} size="sm" />
                    <span className="min-w-0">
                      <span className="block text-xs font-medium text-gold-400">{agent.name}</span>
                      <span className="mt-0.5 block text-xs text-gray-300 line-clamp-2">{item.query}</span>
                      <span className="mt-1 block text-[11px] text-gray-500">{new Date(item.created_at).toLocaleString()}</span>
                    </span>
                  </button>
                )
              })
            )}
          </div>
        </aside>
      </div>
    </AppShell>
  )
}
