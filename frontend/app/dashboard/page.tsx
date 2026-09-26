'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Send, Loader2, Check, AlertCircle, Shield, Brain, Server, Code2, Rocket, Eye, Network, TrendingUp, Paperclip, X } from 'lucide-react'
import AppShell from '../components/AppShell'
import GlassCard from '../components/GlassCard'
import StatusCard from '../components/StatusCard'
import { dukeApi, DukeApiError, DUKE_API_URL, type HealthStatus, type ModelStatus, type LearningStatus } from '@/lib/duke-api'
import { listRecentQueries, saveQuery, type AgentQuery } from '@/lib/query-history'

// DUKE first and visually distinct - it's the central coordinator, not an eighth
// specialist. Drawing on every specialist's knowledge at once (see backend
// /tasks/submit's cross_agent retrieval mode), not just its own slice of it.
const AGENTS = [
  { id: 'duke', name: 'DUKE', icon: Network, isCoordinator: true },
  { id: 'security-expert', name: 'Security Expert', icon: Shield },
  { id: 'ml-expert', name: 'ML Expert', icon: Brain },
  { id: 'systems-expert', name: 'Systems Expert', icon: Server },
  { id: 'backend-expert', name: 'Backend Expert', icon: Code2 },
  { id: 'devops-expert', name: 'DevOps Expert', icon: Rocket },
  { id: 'vision-expert', name: 'Vision Expert', icon: Eye },
  { id: 'advanced-expert', name: 'Emerging Tech Strategist', icon: TrendingUp },
]

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

export default function DashboardPage() {
  const { health, model, learning } = useBackendStatus()

  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [history, setHistory] = useState<AgentQuery[]>([])

  const [query, setQuery] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>(AGENTS[0].id)
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Kept in sync with backend/coordinator_API/core/document_qa.py - capped
  // well under Vercel's ~4.5MB serverless request-body limit (this file is
  // sent base64-encoded, ~4/3 its raw size), not just a file-size opinion.
  const MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    setLoading(true)
    setError(null)

    try {
      let attachment_base64: string | undefined
      let attachment_name: string | undefined
      if (attachedFile) {
        attachment_base64 = await readFileAsBase64(attachedFile)
        attachment_name = attachedFile.name
      }

      const data = await dukeApi.submitTask({
        description: query,
        complexity: 5,
        target_agent: selectedAgent,
        buyer_id: userEmail ?? 'dashboard-user',
        attachment_base64,
        attachment_name,
      })

      const response = data.response || 'No response received'
      setResult(response)
      setQuery('')
      setAttachedFile(null)

      if (userEmail) {
        await saveQuery(selectedAgent, query, response)
        refreshHistory()
      }
    } catch (err) {
      setError(err instanceof DukeApiError ? err.message : 'Query failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
        <p className="text-gray-400">{userEmail ? `Signed in as ${userEmail}` : 'Deploy a specialist agent for any task.'}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <StatusCard
          label="Backend"
          loading={health.loading}
          error={health.error}
          value={health.data?.status === 'ok' ? 'Online' : health.data?.status}
          detail={health.data?.service}
        />
        <StatusCard
          label="Model"
          loading={model.loading}
          error={model.error}
          value={model.data?.status === 'ready' ? 'Ready' : 'Training'}
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <GlassCard>
            <h2 className="text-lg font-semibold text-white mb-5">Ask DUKE or a specialist</h2>

            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Who should answer? <span className="text-gray-500 font-normal">(DUKE draws on every specialist&apos;s knowledge at once)</span>
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {AGENTS.map((agent) => {
                  const Icon = agent.icon
                  const active = selectedAgent === agent.id
                  return (
                    <button
                      key={agent.id}
                      type="button"
                      onClick={() => setSelectedAgent(agent.id)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                        active
                          ? 'bg-gold-500 text-royal-blue-900'
                          : agent.isCoordinator
                            ? 'bg-gold-500/10 border border-gold-500/50 text-gold-400 hover:border-gold-500'
                            : 'bg-white/5 border border-gold-500/20 text-gray-300 hover:border-gold-500/50'
                      }`}
                    >
                      <Icon className="w-4 h-4 shrink-0" />
                      {agent.name}
                    </button>
                  )
                })}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="query" className="block text-sm font-medium text-gray-300 mb-2">
                  Your question
                </label>
                <textarea
                  id="query"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Describe what you need the specialist to help with... (paste a link or attach a file to ask about it)"
                  rows={5}
                  disabled={loading}
                  className="w-full px-4 py-3 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors resize-none"
                />
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md,.csv,.json,.log"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file && file.size > MAX_ATTACHMENT_BYTES) {
                    setError('That file is too large (3MB limit).')
                  } else if (file) {
                    setAttachedFile(file)
                    setError(null)
                  }
                  e.target.value = ''
                }}
              />

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-white/5 border border-gold-500/20 text-gray-300 hover:border-gold-500/50 transition-colors disabled:opacity-50 cursor-pointer"
                >
                  <Paperclip className="w-3.5 h-3.5" /> Attach a file
                </button>
                {attachedFile && (
                  <span className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs bg-gold-500/10 border border-gold-500/30 text-gold-300">
                    {attachedFile.name}
                    <button
                      type="button"
                      onClick={() => setAttachedFile(null)}
                      aria-label="Remove attachment"
                      className="text-gold-400 hover:text-gold-200 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Processing&hellip;
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" /> Send query
                  </>
                )}
              </button>
              {loading && (
                <p className="text-center text-xs text-gray-500">
                  The specialist model runs on-demand and can take up to a minute to respond.
                </p>
              )}
            </form>
          </GlassCard>

          {error && (
            <GlassCard className="border-red-500/40">
              <h3 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> Something went wrong
              </h3>
              <p className="text-red-300 text-sm">{error}</p>
              <p className="text-gray-500 text-xs mt-2">Backend: {DUKE_API_URL}</p>
            </GlassCard>
          )}

          {result && !error && (
            <GlassCard>
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" /> Response
              </h3>
              <p className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">{result}</p>
            </GlassCard>
          )}
        </div>

        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-4">Recent queries</h2>
          <div className="space-y-3 max-h-[28rem] overflow-y-auto">
            {history.length === 0 ? (
              <p className="text-gray-400 text-sm">No queries yet - ask something to get started.</p>
            ) : (
              history.map((item) => {
                const agent = AGENTS.find((a) => a.id === item.agent_id)
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setQuery(item.query)
                      setSelectedAgent(item.agent_id)
                    }}
                    className="w-full text-left p-3 bg-white/5 border border-gold-500/15 rounded-lg hover:border-gold-500/50 transition-colors cursor-pointer"
                  >
                    <p className="text-xs text-gold-500 font-medium mb-1">{agent?.name ?? item.agent_id}</p>
                    <p className="text-xs text-gray-300 line-clamp-2">{item.query}</p>
                    <p className="text-xs text-gray-500 mt-1">{new Date(item.created_at).toLocaleString()}</p>
                  </button>
                )
              })
            )}
          </div>
        </GlassCard>
      </div>
    </AppShell>
  )
}
