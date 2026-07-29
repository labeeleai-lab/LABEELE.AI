'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Loader2,
  RefreshCw,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  UploadCloud,
  FolderUp,
  FileUp,
  X,
  Cpu,
  HardDrive,
  MemoryStick,
  Terminal,
  Info,
  Network,
  Circle,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import StatusCard from '../../components/StatusCard'
import {
  dukeApi,
  DukeApiError,
  type ModelStatus,
  type LearningStatus,
  type TrainingStats,
  type RetrainResult,
  type TrainingExample,
  type TrainingUploadResult,
  type ModelVersionSummary,
  type SystemResources,
  type DashboardSummary,
  type DukeAgent,
} from '@/lib/duke-api'
import { parseTrainingFiles, type ParsedFileResult } from '@/lib/parseTrainingFiles'

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
  const [retrainResult, setRetrainResult] = useState<RetrainResult | null>(null)

  const filesInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [parsedFiles, setParsedFiles] = useState<ParsedFileResult[]>([])
  const [autoRetrain, setAutoRetrain] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<TrainingUploadResult | null>(null)
  const [uploadNotice, setUploadNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Dashboard (Phase 1 - real data only; see backend/coordinator_api.py's
  // "ADMIN DASHBOARD" section for exactly what each field is sourced from)
  const [history, setHistory] = useState<ModelVersionSummary[] | null>(null)
  const [resources, setResources] = useState<SystemResources | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [agents, setAgents] = useState<DukeAgent[] | null>(null)
  const [dashboardError, setDashboardError] = useState<string | null>(null)

  const [logLines, setLogLines] = useState<string[]>([])
  const [logConnected, setLogConnected] = useState(false)

  useEffect(() => {
    folderInputRef.current?.setAttribute('webkitdirectory', 'true')
    folderInputRef.current?.setAttribute('directory', 'true')
  }, [])

  const refreshDashboard = () => {
    dukeApi.trainingHistory().then(setHistory, () => setDashboardError('Could not load training history.'))
    dukeApi.systemResources().then(setResources, () => setDashboardError('Could not load system resources.'))
    dukeApi.dashboardSummary().then(setSummary, () => setDashboardError('Could not load dashboard summary.'))
    dukeApi.listAgents().then(setAgents, () => setDashboardError('Could not load agents.'))
  }

  useEffect(() => {
    refreshDashboard()
    // Real polling, not push - matches every other admin page in this app and
    // is more than adequate at this traffic level (see plan: no WebSocket built).
    const interval = setInterval(refreshDashboard, 25_000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const source = new EventSource('/api/admin/duke/api/logs/stream')
    source.onopen = () => setLogConnected(true)
    source.onerror = () => setLogConnected(false)
    source.onmessage = (event) => {
      setLogLines((prev) => {
        const next = [...prev, event.data]
        return next.length > 200 ? next.slice(next.length - 200) : next
      })
    }
    return () => source.close()
  }, [])

  const allExamples: TrainingExample[] = parsedFiles.flatMap((f) => f.examples)
  const fileErrors = parsedFiles.filter((f) => f.error)

  const handleFilesSelected = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    setUploadResult(null)
    setUploadNotice(null)
    const results = await parseTrainingFiles(fileList)
    setParsedFiles((prev) => [...prev, ...results])
  }

  const removeParsedFile = (fileName: string) => {
    setParsedFiles((prev) => prev.filter((f) => f.fileName !== fileName))
  }

  const clearParsedFiles = () => {
    setParsedFiles([])
    setUploadResult(null)
    setUploadNotice(null)
  }

  const handleUpload = async () => {
    if (allExamples.length === 0) return
    setUploading(true)
    setUploadNotice(null)
    try {
      const result = await dukeApi.uploadTrainingData(allExamples)
      setUploadResult(result)
      setUploadNotice({
        type: 'success',
        message: `Imported ${result.inserted} example(s) - ${result.skipped_duplicate} duplicate, ${result.skipped_invalid} invalid, skipped.`,
      })
      setParsedFiles([])

      if (autoRetrain && result.inserted > 0) {
        await handleRetrain()
      } else {
        refresh()
      }
    } catch (err) {
      setUploadNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Upload failed.' })
    } finally {
      setUploading(false)
    }
  }

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
    setRetrainResult(null)
    try {
      const result = await dukeApi.retrainAgents()
      setRetrainResult(result)
      if (result.status === 'skipped') {
        setNotice({
          type: 'error',
          message: `Skipped - only ${result.usable_samples} usable sample(s) after quality filtering (need 10+).`,
        })
      } else {
        setNotice({ type: 'success', message: `Training run complete - model v${result.model_version}.` })
      }
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
          <p className="text-gray-400 text-sm mb-3">
            Runs a real training pass: filters out error responses, too-short answers, duplicates,
            and anything rated 1-2 stars in Annotate; splits what&apos;s left 85/15 into train/validation
            sets; and stops early once validation stops improving, rather than training a fixed
            number of epochs regardless of overfitting.
          </p>
          <p className="text-gray-500 text-xs mb-5">
            Separate from the offline LoRA fine-tune script (<code>train_duke_offline.py</code>),
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

      <GlassCard className="mt-6">
        <h2 className="font-semibold text-white mb-2">Import training data</h2>
        <p className="text-gray-400 text-sm mb-1">
          Pick files or an entire folder of curated examples and they&apos;re inserted straight into
          the same training pool the pipeline above reads from - the next retrain picks them up
          automatically, with the same quality filtering applied.
        </p>
        <p className="text-gray-500 text-xs mb-5">
          Supported formats: <code>.json</code> (array of objects), <code>.jsonl</code>, and{' '}
          <code>.csv</code>. Each row needs an instruction/prompt/question field and an
          output/response/answer field - e.g. <code>{'{"instruction": "...", "output": "..."}'}</code>.
          An optional <code>persona_id</code> tags which specialist the example targets.
        </p>

        <input
          ref={filesInputRef}
          type="file"
          multiple
          accept=".json,.jsonl,.ndjson,.csv"
          className="hidden"
          onChange={(e) => {
            handleFilesSelected(e.target.files)
            e.target.value = ''
          }}
        />
        <input
          ref={folderInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            handleFilesSelected(e.target.files)
            e.target.value = ''
          }}
        />

        <div className="flex flex-wrap gap-3 mb-5">
          <button
            type="button"
            onClick={() => filesInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-white/5 border border-gold-500/20 text-gray-200 hover:border-gold-500/50 transition-colors cursor-pointer"
          >
            <FileUp className="w-4 h-4" /> Choose files
          </button>
          <button
            type="button"
            onClick={() => folderInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-white/5 border border-gold-500/20 text-gray-200 hover:border-gold-500/50 transition-colors cursor-pointer"
          >
            <FolderUp className="w-4 h-4" /> Choose folder
          </button>
        </div>

        {parsedFiles.length > 0 && (
          <div className="mb-5 space-y-2">
            {parsedFiles.map((f) => (
              <div
                key={f.fileName}
                className={`flex items-center justify-between gap-3 px-3 py-2 rounded-lg border text-sm ${
                  f.error ? 'border-red-500/30 bg-red-500/5 text-red-300' : 'border-gold-500/15 bg-white/5 text-gray-300'
                }`}
              >
                <span className="truncate">{f.fileName}</span>
                <span className="flex items-center gap-3 shrink-0">
                  <span className="text-xs">{f.error ?? `${f.examples.length} example(s)`}</span>
                  <button
                    type="button"
                    onClick={() => removeParsedFile(f.fileName)}
                    aria-label={`Remove ${f.fileName}`}
                    className="text-gray-500 hover:text-gray-300 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}

        {uploadNotice && (
          <div
            role="alert"
            className={`mb-5 p-3 rounded-lg border text-sm flex items-start gap-2.5 ${
              uploadNotice.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-red-500/10 border-red-500/30 text-red-300'
            }`}
          >
            {uploadNotice.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            )}
            {uploadNotice.message}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={handleUpload}
            disabled={uploading || allExamples.length === 0 || fileErrors.length === parsedFiles.length}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold bg-gold-500 text-royal-blue-900 hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
            {uploading ? 'Importing…' : `Import ${allExamples.length} example(s)`}
          </button>

          {parsedFiles.length > 0 && (
            <button
              type="button"
              onClick={clearParsedFiles}
              disabled={uploading}
              className="text-sm text-gray-400 hover:text-gray-200 cursor-pointer disabled:opacity-50"
            >
              Clear selection
            </button>
          )}

          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer ml-auto">
            <input
              type="checkbox"
              checked={autoRetrain}
              onChange={(e) => setAutoRetrain(e.target.checked)}
              className="rounded border-gold-500/40 bg-white/5"
            />
            Retrain automatically after import
          </label>
        </div>

        {uploadResult && (
          <p className="text-xs text-gray-500 mt-4">
            Last import: {uploadResult.inserted} inserted / {uploadResult.total_submitted} submitted
            ({uploadResult.skipped_duplicate} duplicate, {uploadResult.skipped_invalid} invalid).
          </p>
        )}
      </GlassCard>

      {retrainResult && retrainResult.status === 'success' && (
        <GlassCard className="mt-6">
          <h2 className="font-semibold text-white mb-4">Last training run</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
            <div>
              <div className="text-xs text-gray-500 mb-1">Validation accuracy</div>
              <div className="text-lg font-bold text-gold-500">
                {((retrainResult.validation_accuracy ?? 0) * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Epochs run</div>
              <div className="text-lg font-bold text-white">{retrainResult.epochs_run}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Train / val samples</div>
              <div className="text-lg font-bold text-white">
                {retrainResult.train_samples} / {retrainResult.val_samples}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Model version</div>
              <div className="text-lg font-bold text-white">v{retrainResult.model_version}</div>
            </div>
          </div>
          <div className="text-sm text-gray-400">
            Considered {retrainResult.total_samples_considered} total samples - excluded{' '}
            {retrainResult.skipped_error} error-responses, {retrainResult.skipped_short} too-short,{' '}
            {retrainResult.skipped_duplicate} duplicates, and {retrainResult.skipped_low_rated} rated
            low in Annotate.
          </div>
        </GlassCard>
      )}

      <h2 className="text-xl font-bold text-white mt-10 mb-1">Dashboard</h2>
      <p className="text-gray-400 text-sm mb-6">
        Real-time visibility into DUKE and every agent. Everything below is sourced directly from
        the backend - nothing here is estimated or simulated.
      </p>

      {dashboardError && (
        <div role="alert" className="mb-6 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
          {dashboardError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatusCard
          label="Total tasks"
          loading={!summary && !dashboardError}
          value={summary ? String(summary.total_tasks_completed) : undefined}
          detail={summary ? `${summary.total_agents} agents` : undefined}
        />
        <StatusCard
          label="Training samples"
          loading={!summary && !dashboardError}
          value={summary ? String(summary.total_training_samples) : undefined}
        />
        <StatusCard
          label="Knowledge chunks"
          loading={!summary && !dashboardError}
          value={summary ? String(summary.total_knowledge_chunks) : undefined}
          detail={`${summary ? Object.keys(summary.knowledge_chunks_by_agent).length : 0} sources covered`}
        />
        <StatusCard
          label="Latest model"
          loading={!summary && !dashboardError}
          value={summary ? `v${summary.latest_model_version}` : undefined}
          detail={summary?.latest_validation_accuracy != null ? `${(summary.latest_validation_accuracy * 100).toFixed(1)}% accuracy` : undefined}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <GlassCard>
          <h3 className="font-semibold text-white mb-1">Training history</h3>
          <p className="text-gray-500 text-xs mb-4">Real validation accuracy across every training run ever recorded.</p>
          {!history ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : history.length < 2 ? (
            <p className="text-gray-400 text-sm py-8 text-center">
              Not enough training runs yet for a trend - need at least 2 (have {history.length}).
            </p>
          ) : (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={history.map((h) => ({ version: `v${h.version_number}`, accuracy: (h.validation_accuracy ?? 0) * 100 }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="version" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} unit="%" domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#0f1729', border: '1px solid rgba(212,175,55,0.3)', borderRadius: 8, fontSize: 12 }}
                    formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Validation accuracy']}
                  />
                  <Line type="monotone" dataKey="accuracy" stroke="#d4af37" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </GlassCard>

        <GlassCard>
          <h3 className="font-semibold text-white mb-1">Resource monitoring</h3>
          <p className="text-gray-500 text-xs mb-4">Real CPU/memory/disk from the backend process. Refreshes every 25s.</p>
          {!resources ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : (
            <div className="space-y-4">
              <ResourceBar icon={Cpu} label="CPU" percent={resources.cpu_percent} detail={`${resources.cpu_percent.toFixed(0)}%`} />
              <ResourceBar
                icon={MemoryStick}
                label="Memory"
                percent={resources.memory_percent}
                detail={`${resources.memory_used_gb.toFixed(1)} / ${resources.memory_total_gb.toFixed(1)} GB`}
              />
              <ResourceBar
                icon={HardDrive}
                label="Disk"
                percent={resources.disk_percent}
                detail={`${resources.disk_used_gb.toFixed(0)} / ${resources.disk_total_gb.toFixed(0)} GB`}
              />
              <div className="flex items-center justify-between text-sm pt-1 border-t border-gold-500/10">
                <span className="text-gray-400">GPU</span>
                {resources.gpu_available ? (
                  <span className="text-white">{(resources.gpu_utilization ?? 0).toFixed(0)}% utilized</span>
                ) : (
                  <span className="text-gray-500 text-xs">Not available (CPU-only deployment)</span>
                )}
              </div>
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="mb-6">
        <h3 className="font-semibold text-white mb-4">Agents</h3>
        {!agents ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {agents.map((agent) => {
              const isDuke = agent.name === 'duke'
              const knowledgeCount = summary?.knowledge_chunks_by_agent[agent.name] ?? 0
              return (
                <div
                  key={agent.id}
                  className={`p-3 rounded-lg border ${isDuke ? 'border-gold-500/50 bg-gold-500/5' : 'border-gold-500/15 bg-white/5'}`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {isDuke ? <Network className="w-4 h-4 text-gold-500" /> : <Circle className="w-2 h-2 fill-emerald-400 text-emerald-400" />}
                    <span className="text-sm font-medium text-white capitalize">{agent.name.replace(/-/g, ' ')}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <span>Tasks: <span className="text-gray-200">{agent.total_tasks_completed}</span></span>
                    <span>Knowledge: <span className="text-gray-200">{knowledgeCount}</span></span>
                    <span>Reputation: <span className="text-gray-200">{agent.reputation_multiplier?.toFixed(2)}</span></span>
                    <span>Status: <span className="text-gray-200">{agent.status}</span></span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </GlassCard>

      <GlassCard className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Terminal className="w-4 h-4" /> Live system log
          </h3>
          <span className={`text-xs flex items-center gap-1.5 ${logConnected ? 'text-emerald-400' : 'text-gray-500'}`}>
            <Circle className={`w-2 h-2 ${logConnected ? 'fill-emerald-400' : 'fill-gray-600'}`} />
            {logConnected ? 'Live' : 'Connecting…'}
          </span>
        </div>
        <div className="bg-black/40 rounded-lg p-3 h-56 overflow-y-auto font-mono text-xs text-gray-300 space-y-0.5">
          {logLines.length === 0 ? (
            <p className="text-gray-500">Waiting for log activity&hellip;</p>
          ) : (
            logLines.map((line, i) => <div key={i}>{line}</div>)
          )}
        </div>
      </GlassCard>

      <div className="flex items-start gap-2.5 p-4 rounded-lg border border-gray-600/30 bg-white/5 text-xs text-gray-400">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-gray-500" />
        <div>
          <strong className="text-gray-300">Not shown, on purpose:</strong> GPU metrics beyond utilization (no GPU
          exists on this deployment), precision/recall/F1/perplexity/benchmark scores (this training pipeline measures
          validation accuracy via cosine similarity, not classification metrics), and per-agent
          online/synchronizing/updating states (every agent is served by one shared backend process, not
          independent services that can be in those states). These are left out rather than shown with invented numbers.
        </div>
      </div>
    </AdminShell>
  )
}

function ResourceBar({
  icon: Icon,
  label,
  percent,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  percent: number
  detail: string
}) {
  const clamped = Math.min(100, Math.max(0, percent))
  const barColor = clamped > 85 ? 'bg-red-500' : clamped > 65 ? 'bg-amber-500' : 'bg-gold-500'
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="flex items-center gap-1.5 text-gray-300">
          <Icon className="w-3.5 h-3.5" /> {label}
        </span>
        <span className="text-gray-400 text-xs">{detail}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  )
}
