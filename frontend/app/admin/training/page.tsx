'use client'

import { useEffect, useState } from 'react'
import { Loader2, RefreshCw, Trash2, AlertTriangle, CheckCircle2 } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import StatusCard from '../../components/StatusCard'
import { dukeApi, DukeApiError, type ModelStatus, type LearningStatus, type TrainingStats } from '@/lib/duke-api'

function ConfirmButton({
  label,
  confirmLabel,
  onConfirm,
  icon: Icon,
  tone = 'default',
}: {
  label: string
  confirmLabel: string
  onConfirm: () => Promise<void>
  icon: React.ComponentType<{ className?: string }>
  tone?: 'default' | 'danger'
}) {
  const [armed, setArmed] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!armed) return
    const t = setTimeout(() => setArmed(false), 4000)
    return () => clearTimeout(t)
  }, [armed])

  const handleClick = async () => {
    if (!armed) {
      setArmed(true)
      return
    }
    setLoading(true)
    try {
      await onConfirm()
    } finally {
      setLoading(false)
      setArmed(false)
    }
  }

  const toneClasses =
    tone === 'danger'
      ? armed
        ? 'bg-red-500 text-white hover:bg-red-400'
        : 'border border-red-500/40 text-red-400 hover:bg-red-500/10'
      : armed
        ? 'bg-gold-500 text-royal-blue-900 hover:bg-gold-400'
        : 'border border-gold-500/40 text-gold-500 hover:bg-gold-500/10'

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${toneClasses}`}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
      {loading ? 'Working…' : armed ? confirmLabel : label}
    </button>
  )
}

export default function AdminTrainingPage() {
  const [model, setModel] = useState<{ data?: ModelStatus; loading: boolean; error?: string }>({ loading: true })
  const [learning, setLearning] = useState<{ data?: LearningStatus; loading: boolean; error?: string }>({ loading: true })
  const [stats, setStats] = useState<{ data?: TrainingStats; loading: boolean; error?: string }>({ loading: true })
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const refresh = () => {
    setModel({ loading: true })
    setLearning({ loading: true })
    setStats({ loading: true })
    dukeApi.modelStatus().then(
      (data) => setModel({ data, loading: false }),
      (err) => setModel({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
    dukeApi.learningStatus().then(
      (data) => setLearning({ data, loading: false }),
      (err) => setLearning({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
    dukeApi.trainingStats().then(
      (data) => setStats({ data, loading: false }),
      (err) => setStats({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
  }

  useEffect(refresh, [])

  const handleRetrain = async () => {
    setNotice(null)
    try {
      await dukeApi.retrainAgents()
      setNotice({ type: 'success', message: 'Retraining triggered.' })
      refresh()
    } catch (err) {
      setNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Failed to trigger retraining.' })
    }
  }

  const handleClearCache = async () => {
    setNotice(null)
    try {
      const result = await dukeApi.clearTrainingCache()
      setNotice({ type: 'success', message: `Cleared ${result.deleted} cached training sample(s).` })
      refresh()
    } catch (err) {
      setNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Failed to clear cache.' })
    }
  }

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Training</h1>
      <p className="text-gray-400 mb-8">Controls for the in-process retraining pipeline.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <StatusCard
          label="Model"
          loading={model.loading}
          error={model.error}
          value={model.data?.status === 'ready' ? 'Ready' : 'Training'}
          detail={model.data ? `v${model.data.version} · ${(model.data.accuracy * 100).toFixed(1)}% accuracy` : undefined}
        />
        <StatusCard
          label="Training samples"
          loading={learning.loading}
          error={learning.error}
          value={learning.data ? String(learning.data.total_samples_trained) : undefined}
          detail={learning.data ? `Model ${learning.data.model_version}` : undefined}
        />
        <StatusCard
          label="Estimated cost"
          loading={stats.loading}
          error={stats.error}
          value={stats.data ? `$${(stats.data.data.estimated_cost_usd ?? 0).toFixed(2)}` : undefined}
          detail={stats.data?.data.total_calls !== undefined ? `${stats.data.data.total_calls} calls logged` : undefined}
        />
      </div>

      {notice && (
        <div
          role="alert"
          className={`mb-6 p-4 rounded-lg border text-sm flex items-start gap-2.5 ${
            notice.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
          }`}
        >
          {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
          {notice.message}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard>
          <h2 className="font-semibold text-white mb-2">Retrain agents</h2>
          <p className="text-gray-400 text-sm mb-5">
            Triggers the in-process retraining pipeline against samples collected so far. This is
            separate from the offline LoRA fine-tune script (<code className="text-xs">train_duke_offline.py</code>),
            which runs as its own standalone GPU job and can&apos;t be triggered from here.
          </p>
          <ConfirmButton label="Retrain agents" confirmLabel="Click again to confirm" icon={RefreshCw} onConfirm={handleRetrain} />
        </GlassCard>

        <GlassCard className="border-red-500/20">
          <h2 className="font-semibold text-white mb-2">Clear training cache</h2>
          <p className="text-gray-400 text-sm mb-5">
            Permanently deletes collected training samples. This can&apos;t be undone.
          </p>
          <ConfirmButton label="Clear cache" confirmLabel="Click again to confirm" icon={Trash2} tone="danger" onConfirm={handleClearCache} />
        </GlassCard>
      </div>
    </AdminShell>
  )
}
