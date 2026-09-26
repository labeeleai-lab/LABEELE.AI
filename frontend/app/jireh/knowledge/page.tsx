'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Loader2,
  UploadCloud,
  FileUp,
  Trash2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Globe2,
  Circle,
} from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import { dukeApi, DukeApiError, type PersonaConfig, type KnowledgeSource, type KnowledgeChunkDetail } from '@/lib/duke-api'

function ConfirmDeleteButton({ label, onConfirm }: { label: string; onConfirm: () => Promise<void> }) {
  const [armed, setArmed] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!armed) return
    const t = setTimeout(() => setArmed(false), 4000)
    return () => clearTimeout(t)
  }, [armed])

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation()
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

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      title={armed ? 'Click again to confirm' : label}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 ${
        armed ? 'bg-red-500 text-white' : 'text-gray-500 hover:text-red-400 hover:bg-red-500/10'
      }`}
    >
      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
      {armed && 'Confirm?'}
    </button>
  )
}

type Scope = { type: 'global' } | { type: 'agent'; personaId: string; personaName: string }

export default function AdminKnowledgePage() {
  const [personas, setPersonas] = useState<PersonaConfig[] | null>(null)
  const [scope, setScope] = useState<Scope>({ type: 'global' })

  const [sources, setSources] = useState<KnowledgeSource[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)

  const [sourceName, setSourceName] = useState('')
  const [pasteText, setPasteText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadNotice, setUploadNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [expandedSource, setExpandedSource] = useState<string | null>(null)
  const [chunksBySource, setChunksBySource] = useState<Record<string, KnowledgeChunkDetail[]>>({})
  const [chunksLoading, setChunksLoading] = useState<string | null>(null)

  useEffect(() => {
    dukeApi.listPersonas().then(setPersonas, () => setPersonas([]))
  }, [])

  const loadSources = async (s: Scope) => {
    setListError(null)
    setSources(null)
    try {
      const data = s.type === 'global' ? await dukeApi.listKnowledge('global') : await dukeApi.listKnowledge('agent', s.personaId)
      setSources(data)
    } catch (err) {
      setListError(err instanceof DukeApiError ? err.message : 'Could not reach the Duke backend.')
      setSources([])
    }
  }

  useEffect(() => {
    loadSources(scope)
    setExpandedSource(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope.type, scope.type === 'agent' ? scope.personaId : null])

  const selectScope = (s: Scope) => {
    setScope(s)
    setUploadNotice(null)
  }

  const toggleExpand = async (sourceId: string) => {
    if (expandedSource === sourceId) {
      setExpandedSource(null)
      return
    }
    setExpandedSource(sourceId)
    if (!chunksBySource[sourceId]) {
      setChunksLoading(sourceId)
      try {
        const chunks = await dukeApi.getKnowledgeSourceChunks(sourceId)
        setChunksBySource((prev) => ({ ...prev, [sourceId]: chunks }))
      } catch {
        setChunksBySource((prev) => ({ ...prev, [sourceId]: [] }))
      } finally {
        setChunksLoading(null)
      }
    }
  }

  const handlePasteUpload = async () => {
    if (!pasteText.trim() || !sourceName.trim()) return
    setUploading(true)
    setUploadNotice(null)
    try {
      const personaId = scope.type === 'global' ? null : scope.personaId
      const result = await dukeApi.uploadKnowledgeText({ personaId, sourceName: sourceName.trim(), text: pasteText })
      setUploadNotice({ type: 'success', message: `Added "${sourceName}" - ${result.chunks_created} chunk(s).` })
      setPasteText('')
      setSourceName('')
      await loadSources(scope)
    } catch (err) {
      setUploadNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Upload failed.' })
    } finally {
      setUploading(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setUploadNotice(null)
    try {
      const personaId = scope.type === 'global' ? null : scope.personaId
      const ext = file.name.split('.').pop()?.toLowerCase()
      let result
      if (ext === 'pdf') {
        const dataUrl: string = await new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(file)
        })
        const base64 = dataUrl.split(',')[1] ?? ''
        result = await dukeApi.uploadKnowledgePdf({ personaId, sourceName: file.name, fileBase64: base64 })
      } else {
        const text = await file.text()
        result = await dukeApi.uploadKnowledgeText({ personaId, sourceName: file.name, text, markdown: ext === 'md' })
      }
      setUploadNotice({ type: 'success', message: `Added "${file.name}" - ${result.chunks_created} chunk(s).` })
      await loadSources(scope)
    } catch (err) {
      setUploadNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Upload failed.' })
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteSource = async (sourceId: string) => {
    await dukeApi.deleteKnowledgeSource(sourceId)
    await loadSources(scope)
  }

  const handleDeleteChunk = async (sourceId: string, chunkId: string) => {
    await dukeApi.deleteKnowledgeChunk(chunkId)
    setChunksBySource((prev) => ({ ...prev, [sourceId]: (prev[sourceId] || []).filter((c) => c.id !== chunkId) }))
    await loadSources(scope)
  }

  const scopeLabel = scope.type === 'global' ? 'DUKE Global' : scope.personaName

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Knowledge</h1>
      <p className="text-gray-400 mb-8">
        Train DUKE or any individual agent with documents. Uploaded content is chunked, embedded, and retrieved live
        in real responses on <code>/tasks/submit</code> - no redeploy needed once this backend change is live.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-1 h-fit">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">Scope</h2>
          <ul className="space-y-1.5">
            <li>
              <button
                onClick={() => selectScope({ type: 'global' })}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer flex items-center gap-2 ${
                  scope.type === 'global'
                    ? 'bg-gold-500/15 text-gold-500 border border-gold-500/30'
                    : 'text-gray-300 hover:bg-white/5 border border-transparent'
                }`}
              >
                <Globe2 className="w-3.5 h-3.5 shrink-0" />
                DUKE Global
              </button>
            </li>
          </ul>
          <div className="h-px bg-gold-500/10 my-3" />
          {!personas ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading agents&hellip;
            </div>
          ) : (
            <ul className="space-y-1.5">
              {personas.map((p) => (
                <li key={p.persona_id}>
                  <button
                    onClick={() => selectScope({ type: 'agent', personaId: p.persona_id, personaName: p.name })}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer flex items-center gap-2 ${
                      scope.type === 'agent' && scope.personaId === p.persona_id
                        ? 'bg-gold-500/15 text-gold-500 border border-gold-500/30'
                        : 'text-gray-300 hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <Circle className={`w-2 h-2 shrink-0 ${p.is_active ? 'fill-emerald-400 text-emerald-400' : 'fill-gray-600 text-gray-600'}`} />
                    {p.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <div className="lg:col-span-2 space-y-6">
          <GlassCard>
            <h2 className="font-semibold text-white mb-1">Add knowledge to {scopeLabel}</h2>
            <p className="text-gray-400 text-sm mb-5">
              Paste text below, or upload a <code>.txt</code>, <code>.md</code>, or <code>.pdf</code> file.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFileUpload(file)
                e.target.value = ''
              }}
            />

            <div className="space-y-3 mb-4">
              <input
                type="text"
                placeholder={'Label for this knowledge (e.g. "Refund policy")'}
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors text-sm"
              />
              <textarea
                placeholder="Paste text or markdown here..."
                rows={6}
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors text-sm resize-y"
              />
            </div>

            {uploadNotice && (
              <div
                role="alert"
                className={`mb-4 p-3 rounded-lg border text-sm flex items-start gap-2.5 ${
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

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handlePasteUpload}
                disabled={uploading || !pasteText.trim() || !sourceName.trim()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold bg-gold-500 text-royal-blue-900 hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                Add text
              </button>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-white/5 border border-gold-500/20 text-gray-200 hover:border-gold-500/50 transition-colors cursor-pointer disabled:opacity-50"
              >
                <FileUp className="w-4 h-4" /> Upload file
              </button>
            </div>
          </GlassCard>

          <GlassCard>
            <h2 className="font-semibold text-white mb-4">Knowledge for {scopeLabel}</h2>

            {listError && (
              <div role="alert" className="mb-4 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
                {listError}
              </div>
            )}

            {!sources ? (
              <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
              </div>
            ) : sources.length === 0 ? (
              <p className="text-gray-400 text-sm">No knowledge added yet for {scopeLabel}.</p>
            ) : (
              <ul className="space-y-2">
                {sources.map((source) => {
                  const expanded = expandedSource === source.source_id
                  return (
                    <li key={source.source_id} className="border border-gold-500/15 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleExpand(source.source_id)}
                        className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-white/5 hover:bg-white/10 transition-colors cursor-pointer text-left"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          {expanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="text-sm text-white truncate">{source.source_name}</p>
                            <p className="text-xs text-gray-500 truncate">{source.preview}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className="text-xs text-gray-500">{source.chunk_count} chunk(s)</span>
                          <ConfirmDeleteButton label="Delete source" onConfirm={() => handleDeleteSource(source.source_id)} />
                        </div>
                      </button>

                      {expanded && (
                        <div className="px-4 py-3 bg-black/20 space-y-2">
                          {chunksLoading === source.source_id ? (
                            <div className="flex items-center gap-2 text-gray-400 text-xs py-2">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading chunks&hellip;
                            </div>
                          ) : (
                            (chunksBySource[source.source_id] || []).map((chunk) => (
                              <div
                                key={chunk.id}
                                className="flex items-start justify-between gap-3 p-3 bg-white/5 rounded-lg border border-gold-500/10"
                              >
                                <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{chunk.content}</p>
                                <ConfirmDeleteButton
                                  label="Delete chunk"
                                  onConfirm={() => handleDeleteChunk(source.source_id, chunk.id)}
                                />
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </GlassCard>
        </div>
      </div>
    </AdminShell>
  )
}
