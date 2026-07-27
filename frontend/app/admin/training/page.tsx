'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2, RefreshCw, Trash2, AlertTriangle, CheckCircle2, UploadCloud, FolderUp, FileUp, X } from 'lucide-react'
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

  useEffect(() => {
    folderInputRef.current?.setAttribute('webkitdirectory', 'true')
    folderInputRef.current?.setAttribute('directory', 'true')
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
    </AdminShell>
  )
}
