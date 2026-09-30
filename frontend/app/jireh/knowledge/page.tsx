'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Loader2,
  UploadCloud,
  FileUp,
  Trash2,
  ChevronDown,
  ChevronRight,
  Globe2,
  BookOpen,
} from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import { dukeApi, DukeApiError, type PersonaConfig, type KnowledgeSource, type KnowledgeChunkDetail } from '@/lib/duke-api'
import { Alert, EmptyState, LoadingRow, PageHeader, SectionTitle } from '../../components/ui'

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
      aria-label={armed ? `Confirm: ${label}` : label}
      className={`flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 ${
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
      <PageHeader eyebrow="JIREH · Model" title="Knowledge" description="Give DUKE or any single persona documents to draw on. Content is split into passages and searched live on every question - answers cite the sources they used." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <nav aria-label="Knowledge scope" className="surface h-fit p-3 lg:col-span-1">
          <p className="px-3 pt-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">Shared</p>
          <button
            type="button"
            onClick={() => selectScope({ type: 'global' })}
            aria-current={scope.type === 'global' ? 'true' : undefined}
            className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer ${
              scope.type === 'global' ? 'bg-white/[0.07] font-medium text-white' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-100'
            }`}
          >
            <Globe2 className="h-4 w-4 shrink-0 text-gold-400" aria-hidden="true" />
            DUKE Global
          </button>
          <p className="px-3 pt-4 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">Personas</p>
          {!personas ? (
            <LoadingRow label="Loading personas…" className="px-3" />
          ) : personas.length === 0 ? (
            <p className="px-3 pb-2 text-xs text-gray-500">No personas available.</p>
          ) : (
            <ul className="space-y-0.5">
              {personas.map((p) => {
                const active = scope.type === 'agent' && scope.personaId === p.persona_id
                return (
                  <li key={p.persona_id}>
                    <button
                      type="button"
                      onClick={() => selectScope({ type: 'agent', personaId: p.persona_id, personaName: p.name })}
                      aria-current={active ? 'true' : undefined}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer ${
                        active ? 'bg-white/[0.07] font-medium text-white' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-100'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${p.is_active ? 'bg-emerald-400' : 'bg-gray-600'}`}
                        aria-hidden="true"
                      />
                      <span className="truncate">{p.name}</span>
                      {!p.is_active && <span className="badge badge-neutral ml-auto">Inactive</span>}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </nav>

        <div className="min-w-0 space-y-6 lg:col-span-2">
          <section className="surface p-5 sm:p-6" aria-labelledby="add-knowledge">
            <SectionTitle
              description={
                <>
                  Paste text below, or upload a <code className="font-mono text-gold-200">.txt</code>,{' '}
                  <code className="font-mono text-gold-200">.md</code>, or <code className="font-mono text-gold-200">.pdf</code> file.
                </>
              }
            >
              <span id="add-knowledge">Add knowledge to {scopeLabel}</span>
            </SectionTitle>

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

            <div className="mb-4 space-y-3">
              <div>
                <label htmlFor="knowledge-label" className="label">
                  Label
                </label>
                <input
                  id="knowledge-label"
                  type="text"
                  placeholder={'e.g. "Refund policy"'}
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label htmlFor="knowledge-text" className="label">
                  Content
                </label>
                <textarea
                  id="knowledge-text"
                  placeholder="Paste text or markdown here..."
                  rows={6}
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                  className="input resize-y"
                />
              </div>
            </div>

            {uploadNotice && (
              <Alert tone={uploadNotice.type} className="mb-4">
                {uploadNotice.message}
              </Alert>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handlePasteUpload}
                disabled={uploading || !pasteText.trim() || !sourceName.trim()}
                className="btn btn-primary"
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <UploadCloud className="h-4 w-4" aria-hidden="true" />}
                Add text
              </button>
              <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn btn-secondary">
                <FileUp className="h-4 w-4" aria-hidden="true" /> Upload file
              </button>
            </div>
          </section>

          <section className="surface p-5 sm:p-6" aria-labelledby="knowledge-list">
            <SectionTitle
              actions={
                sources && sources.length > 0 ? (
                  <span className="badge badge-neutral">
                    {sources.length} source{sources.length === 1 ? '' : 's'}
                  </span>
                ) : undefined
              }
            >
              <span id="knowledge-list">Knowledge for {scopeLabel}</span>
            </SectionTitle>

            {listError && (
              <Alert tone="error" className="mb-4">
                {listError}
              </Alert>
            )}

            {listError ? null : !sources ? (
              <LoadingRow />
            ) : sources.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title={`No knowledge for ${scopeLabel} yet`}
                description="Add text or upload a document above. It is searched on every question from then on."
              />
            ) : (
              <ul className="space-y-2">
                {sources.map((source) => {
                  const expanded = expandedSource === source.source_id
                  return (
                    <li key={source.source_id} className="surface-inset overflow-hidden">
                      <div className="flex items-center gap-2 pr-2">
                        <button
                          type="button"
                          onClick={() => toggleExpand(source.source_id)}
                          aria-expanded={expanded}
                          className="flex min-w-0 flex-1 items-center gap-2.5 px-4 py-3 text-left transition-colors hover:bg-white/[0.03] cursor-pointer"
                        >
                          {expanded ? (
                            <ChevronDown className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                          ) : (
                            <ChevronRight className="h-4 w-4 shrink-0 text-gray-500" aria-hidden="true" />
                          )}
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-medium text-white">{source.source_name}</span>
                            <span className="block truncate text-xs text-gray-500">{source.preview}</span>
                          </span>
                          <span className="badge badge-neutral ml-auto shrink-0">
                            {source.chunk_count} passage{source.chunk_count === 1 ? '' : 's'}
                          </span>
                        </button>
                        <ConfirmDeleteButton label={`Delete ${source.source_name}`} onConfirm={() => handleDeleteSource(source.source_id)} />
                      </div>

                      {expanded && (
                        <div className="space-y-2 border-t border-white/5 bg-black/20 px-4 py-3">
                          {chunksLoading === source.source_id ? (
                            <LoadingRow label="Loading passages…" />
                          ) : (
                            (chunksBySource[source.source_id] || []).map((chunk) => (
                              <div
                                key={chunk.id}
                                className="flex items-start justify-between gap-3 rounded-lg border border-white/5 bg-white/[0.03] p-3"
                              >
                                <p className="whitespace-pre-wrap text-xs leading-relaxed text-gray-300">{chunk.content}</p>
                                <ConfirmDeleteButton label="Delete passage" onConfirm={() => handleDeleteChunk(source.source_id, chunk.id)} />
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
          </section>
        </div>
      </div>
    </AdminShell>
  )
}
