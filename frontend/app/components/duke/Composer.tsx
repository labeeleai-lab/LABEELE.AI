'use client'

import { useEffect, useRef, type KeyboardEvent } from 'react'
import { ArrowUp, Loader2, Paperclip, X } from 'lucide-react'
import { AGENTS, getAgent } from './agents'

// Kept in sync with backend/coordinator_API/core/document_qa.py - capped
// well under Vercel's ~4.5MB serverless request-body limit (this file is
// sent base64-encoded, ~4/3 its raw size), not just a file-size opinion.
export const MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024

interface ComposerProps {
  query: string
  onQueryChange: (q: string) => void
  selectedAgent: string
  onAgentChange: (id: string) => void
  attachedFile: File | null
  onAttach: (file: File | null) => void
  onAttachError: (msg: string) => void
  onSubmit: () => void
  loading: boolean
}

export default function Composer({
  query,
  onQueryChange,
  selectedAgent,
  onAgentChange,
  attachedFile,
  onAttach,
  onAttachError,
  onSubmit,
  loading,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chipRefs = useRef<(HTMLButtonElement | null)[]>([])
  const agent = getAgent(selectedAgent)
  const canSend = query.trim().length > 0 && !loading

  // Auto-grow the textarea with its content, up to a cap (then it scrolls)
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 280)}px`
  }, [query])

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      if (canSend) onSubmit()
    }
  }

  // Radio-group keyboard pattern: arrows move + select, one tab stop
  const onChipKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0
    if (!delta) return
    e.preventDefault()
    const next = (index + delta + AGENTS.length) % AGENTS.length
    onAgentChange(AGENTS[next].id)
    chipRefs.current[next]?.focus()
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (canSend) onSubmit()
      }}
      className="glass-panel p-3 sm:p-4"
      aria-label="Ask DUKE or a specialist"
    >
      <div className="mb-3 flex items-baseline justify-between gap-3 px-1">
        <h2 id="agent-picker-label" className="text-sm font-semibold text-white">
          Ask DUKE or a specialist
        </h2>
        <p className="hidden text-xs text-gray-500 sm:block">DUKE draws on every specialist&apos;s knowledge at once</p>
      </div>

      <div
        role="radiogroup"
        aria-labelledby="agent-picker-label"
        // Swipeable single row on phones; wraps on wider screens so no
        // specialist is ever hidden off the edge
        className="hide-scrollbar -mx-1 mb-3 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible"
      >
        {AGENTS.map((a, i) => {
          const Icon = a.icon
          const active = a.id === selectedAgent
          return (
            <button
              key={a.id}
              ref={(el) => {
                chipRefs.current[i] = el
              }}
              type="button"
              role="radio"
              aria-checked={active}
              tabIndex={active ? 0 : -1}
              onClick={() => onAgentChange(a.id)}
              onKeyDown={(e) => onChipKeyDown(e, i)}
              disabled={loading}
              title={a.focus}
              className={`flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-[13px] font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer ${
                active
                  ? 'border-gold-500 bg-gold-500 text-royal-blue-900 shadow-[0_4px_16px_-6px_rgba(212,175,55,0.6)]'
                  : a.isCoordinator
                    ? 'border-gold-500/40 bg-gold-500/10 text-gold-300 hover:border-gold-500/80 hover:bg-gold-500/15'
                    : 'border-white/10 bg-white/[0.04] text-gray-300 hover:border-gold-500/40 hover:text-white'
              }`}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {a.name}
            </button>
          )
        })}
      </div>

      <div className="glass-inset rounded-xl transition-shadow duration-200 focus-within:border-gold-500/50 focus-within:shadow-gold-ring">
        <label htmlFor="duke-query" className="sr-only">
          Your question for {agent.name}
        </label>
        <textarea
          id="duke-query"
          ref={textareaRef}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={onKeyDown}
          rows={3}
          disabled={loading}
          aria-describedby="duke-query-hint"
          placeholder={
            agent.isCoordinator
              ? 'Ask DUKE anything - it routes across every specialist. Paste a link or attach a file to ask about it.'
              : `Ask the ${agent.name} about ${agent.focus.toLowerCase()}...`
          }
          className="composer-input block max-h-[280px] w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-[15px] leading-relaxed text-white placeholder-gray-500 disabled:opacity-60"
        />

        <div className="flex flex-wrap items-center gap-2 px-2.5 pb-2.5">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.csv,.json,.log"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file && file.size > MAX_ATTACHMENT_BYTES) {
                onAttachError('That file is too large (3MB limit).')
              } else if (file) {
                onAttach(file)
              }
              e.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
            aria-label="Attach a file"
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-400 transition-colors hover:bg-white/5 hover:text-gold-400 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
          >
            <Paperclip className="h-4 w-4" />
            <span className="hidden sm:inline">Attach</span>
          </button>

          {attachedFile && (
            <span className="flex min-w-0 max-w-[14rem] items-center gap-1.5 rounded-lg border border-gold-500/30 bg-gold-500/10 py-1 pr-1 pl-2.5 text-xs text-gold-200">
              <span className="truncate">{attachedFile.name}</span>
              <button
                type="button"
                onClick={() => onAttach(null)}
                aria-label={`Remove attachment ${attachedFile.name}`}
                className="rounded p-0.5 text-gold-400 hover:bg-gold-500/20 hover:text-gold-100 cursor-pointer"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}

          <p id="duke-query-hint" className="ml-auto hidden text-[11px] text-gray-500 md:block">
            <kbd className="rounded border border-white/10 px-1 font-sans">Enter</kbd> to send ·{' '}
            <kbd className="rounded border border-white/10 px-1 font-sans">Shift</kbd>+
            <kbd className="rounded border border-white/10 px-1 font-sans">Enter</kbd> for a new line
          </p>

          <button
            type="submit"
            disabled={!canSend}
            aria-label={loading ? `${agent.name} is working on your question` : `Send to ${agent.name}`}
            className="ml-auto flex h-9 items-center gap-2 rounded-lg bg-gold-500 px-3.5 text-sm font-semibold text-royal-blue-900 transition-all duration-200 hover:bg-gold-400 hover:shadow-[0_6px_20px_-6px_rgba(212,175,55,0.7)] active:scale-[0.97] disabled:cursor-not-allowed disabled:bg-gold-500/30 disabled:text-royal-blue-900/60 disabled:shadow-none md:ml-0 cursor-pointer"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
            <span>{loading ? 'Working' : 'Send'}</span>
          </button>
        </div>
      </div>
    </form>
  )
}
