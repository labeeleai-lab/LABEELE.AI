'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, BookOpen, Info, Paperclip, RotateCcw, XCircle } from 'lucide-react'
import MarkdownMessage, { CopyButton } from './MarkdownMessage'
import { getAgent, type DukeAgent } from './agents'
import type { ParsedResponse } from './parseResponse'

export type Turn =
  | { kind: 'user'; id: string; agentId: string; text: string; attachment?: string; at: Date }
  | { kind: 'pending'; id: string; agentId: string; startedAt: number }
  | { kind: 'assistant'; id: string; agentId: string; parsed: ParsedResponse; at: Date; seconds: number }
  | { kind: 'error'; id: string; agentId: string; message: string; retryText: string }

function AgentAvatar({ agent, size = 'md', className = '' }: { agent: DukeAgent; size?: 'sm' | 'md'; className?: string }) {
  const Icon = agent.icon
  const dims = size === 'sm' ? 'h-7 w-7' : 'h-9 w-9'
  return (
    <span
      aria-hidden="true"
      className={`${dims} ${className || 'grid'} shrink-0 place-items-center rounded-xl border ${
        agent.isCoordinator
          ? 'border-gold-500/50 bg-gradient-to-br from-gold-500/25 to-gold-500/5 text-gold-400'
          : 'border-royal-blue-300/25 bg-gradient-to-br from-royal-blue-500/40 to-royal-blue-800/40 text-royal-blue-100'
      }`}
    >
      <Icon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
    </span>
  )
}

function RoleBadge({ agent }: { agent: DukeAgent }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
        agent.isCoordinator ? 'bg-gold-500/15 text-gold-400' : 'bg-royal-blue-500/30 text-royal-blue-100'
      }`}
    >
      {agent.isCoordinator ? 'Coordinator' : 'Specialist'}
    </span>
  )
}

const time = (d: Date) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

export function UserMessage({ turn }: { turn: Extract<Turn, { kind: 'user' }> }) {
  const agent = getAgent(turn.agentId)
  return (
    <div className="flex animate-message-in justify-end">
      <div className="max-w-[85%] sm:max-w-[75%]">
        <div className="rounded-2xl rounded-tr-md border border-royal-blue-300/20 bg-royal-blue-500/35 px-4 py-3 text-[15px] leading-relaxed text-white shadow-glass">
          <p className="whitespace-pre-wrap break-words">{turn.text}</p>
          {turn.attachment && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-royal-blue-100/80">
              <Paperclip className="h-3 w-3" /> {turn.attachment}
            </p>
          )}
        </div>
        <p className="mt-1.5 text-right text-[11px] text-gray-500">
          To {agent.name} · {time(turn.at)}
        </p>
      </div>
    </div>
  )
}

export function AssistantMessage({ turn }: { turn: Extract<Turn, { kind: 'assistant' }> }) {
  const agent = getAgent(turn.agentId)
  const { parsed } = turn
  const toneFrame =
    parsed.tone === 'error'
      ? 'border-red-400/30'
      : parsed.tone === 'warning'
        ? 'border-amber-400/30'
        : agent.isCoordinator
          ? 'border-gold-500/20'
          : ''

  return (
    <article className="flex animate-message-in gap-3" aria-label={`Response from ${agent.name}`}>
      <AgentAvatar agent={agent} className="hidden sm:grid" />
      <div className={`glass-raised min-w-0 flex-1 overflow-hidden ${toneFrame}`}>
        <header className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-white/5 px-4 py-2.5 sm:px-5">
          <span className="font-semibold text-white">{agent.name}</span>
          <RoleBadge agent={agent} />
          {parsed.origin && (
            <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-medium text-gray-400">
              {parsed.origin}
            </span>
          )}
          <span className="ml-auto text-[11px] text-gray-500">
            {time(turn.at)} · {turn.seconds < 1 ? '<1' : Math.round(turn.seconds)}s
          </span>
        </header>

        <div className="px-4 py-4 sm:px-5">
          {parsed.tone !== 'answer' ? (
            <div className={`flex gap-2.5 text-[15px] leading-7 ${parsed.tone === 'error' ? 'text-red-200' : 'text-amber-100'}`}>
              {parsed.tone === 'error' ? (
                <XCircle className="mt-1 h-4 w-4 shrink-0 text-red-400" />
              ) : (
                <AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-amber-400" />
              )}
              <p className="min-w-0 break-words">{parsed.body}</p>
            </div>
          ) : (
            <MarkdownMessage content={parsed.body} />
          )}
        </div>

        {(parsed.sources.length > 0 || parsed.notice || parsed.tone === 'answer') && (
          <footer className="flex flex-wrap items-center gap-2 border-t border-white/5 px-4 py-2.5 sm:px-5">
            {parsed.sources.length > 0 && (
              <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                <span className="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider text-gray-500">
                  <BookOpen className="h-3 w-3" /> Sources
                </span>
                {parsed.sources.map((s) => (
                  <span
                    key={s}
                    title={s}
                    className="max-w-[16rem] truncate rounded-md border border-gold-500/25 bg-gold-500/[0.07] px-2 py-0.5 text-[11px] text-gold-200"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
            {parsed.notice && (
              <p className="flex min-w-0 items-start gap-1.5 text-xs text-gray-400">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-royal-blue-200" />
                <span>{parsed.notice}</span>
              </p>
            )}
            {parsed.tone === 'answer' && <CopyButton text={parsed.body} label="Copy answer" className="ml-auto" />}
          </footer>
        )}
      </div>
    </article>
  )
}

export function PendingMessage({ turn }: { turn: Extract<Turn, { kind: 'pending' }> }) {
  const agent = getAgent(turn.agentId)
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - turn.startedAt) / 1000)), 1000)
    return () => clearInterval(t)
  }, [turn.startedAt])

  // Honest status: these describe what the backend actually does for every
  // question (retrieve from the knowledge base, then generate) - no fake
  // per-step progress, since the backend doesn't report steps.
  const status = agent.isCoordinator
    ? 'Consulting every specialist’s knowledge and composing an answer'
    : `Searching the ${agent.name}’s knowledge base and composing an answer`

  return (
    <div className="flex animate-message-in gap-3" role="status" aria-live="polite">
      <AgentAvatar agent={agent} className="hidden sm:grid" />
      <div className="glass-raised min-w-0 flex-1 overflow-hidden">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-white/5 px-4 py-2.5 sm:px-5">
          <span className="font-semibold text-white">{agent.name}</span>
          <RoleBadge agent={agent} />
          <span className="ml-auto flex items-center gap-1.5 text-[11px] text-gray-400" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 animate-dot-bounce rounded-full bg-gold-500"
                style={{ animationDelay: `${i * 160}ms` }}
              />
            ))}
          </span>
        </div>
        <div className="space-y-3 px-4 py-4 sm:px-5">
          <p className="text-sm text-gray-300">
            {status}
            <span className="text-gray-500"> · {elapsed}s</span>
          </p>
          <div className="space-y-2" aria-hidden="true">
            <div className="shimmer-line h-2.5 w-[92%] animate-shimmer rounded-full" />
            <div className="shimmer-line h-2.5 w-[78%] animate-shimmer rounded-full" />
            <div className="shimmer-line h-2.5 w-[64%] animate-shimmer rounded-full" />
          </div>
          {elapsed >= 20 && (
            <p className="text-xs text-gray-500">
              DUKE runs its own model on dedicated hardware - detailed answers can take a minute or two.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export function ErrorMessage({
  turn,
  onRetry,
  disabled,
}: {
  turn: Extract<Turn, { kind: 'error' }>
  onRetry: () => void
  disabled: boolean
}) {
  return (
    <div role="alert" className="flex animate-message-in gap-3">
      <span aria-hidden="true" className="hidden h-9 w-9 shrink-0 sm:grid place-items-center rounded-xl border border-red-400/40 bg-red-500/10 text-red-400">
        <XCircle className="h-4 w-4" />
      </span>
      <div className="glass-raised min-w-0 flex-1 border-red-400/30 px-4 py-3.5 sm:px-5">
        <p className="font-semibold text-red-300">The request didn&apos;t complete</p>
        <p className="mt-1 break-words text-sm text-red-200/80">{turn.message}</p>
        <button
          type="button"
          onClick={onRetry}
          disabled={disabled}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-200 transition-colors hover:border-gold-500/50 hover:text-gold-300 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Try again
        </button>
      </div>
    </div>
  )
}

export { AgentAvatar }
