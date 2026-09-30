import { AlertTriangle, Info } from 'lucide-react'

export function HintIcon({ text }: { text: string }) {
  return (
    <span className="group/hint relative inline-flex align-middle font-normal normal-case tracking-normal">
      <button type="button" aria-label={text} className="rounded-full text-gray-500 hover:text-gray-300 cursor-help">
        <Info className="h-3 w-3" aria-hidden="true" />
      </button>
      <span
        role="tooltip"
        className="surface-overlay pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-60 -translate-x-1/2 px-3 py-2 text-xs leading-relaxed text-gray-300 opacity-0
          transition-opacity duration-150 group-hover/hint:opacity-100 group-focus-within/hint:opacity-100"
      >
        {text}
      </span>
    </span>
  )
}

export type StatusTone = 'good' | 'warn' | 'neutral'

const DOT: Record<StatusTone, string> = {
  good: 'bg-emerald-400',
  warn: 'bg-amber-400',
  neutral: 'bg-gray-500',
}

// Metric card. `tone` adds a status dot next to the value (e.g. Online =
// good); leave it out for plain numbers.
export default function StatusCard({
  label,
  value,
  detail,
  loading,
  error,
  hint,
  tone,
}: {
  label: string
  value?: string
  detail?: string
  loading: boolean
  error?: string | null
  hint?: string
  tone?: StatusTone
}) {
  return (
    <div className="surface flex min-h-[6.5rem] flex-col justify-between p-5">
      <div className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
        {label}
        {hint && <HintIcon text={hint} />}
      </div>
      {loading ? (
        <div role="status" aria-label={`${label}: loading`} className="space-y-2">
          <div className="shimmer-line h-5 w-24 animate-shimmer rounded-md" />
          <div className="shimmer-line h-3 w-32 animate-shimmer rounded" />
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-amber-300" title={error}>
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          <span className="text-base font-semibold">Offline</span>
          <span className="sr-only">: {error}</span>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-2 text-xl font-semibold tracking-tight text-white">
            {tone && <span aria-hidden="true" className={`h-2 w-2 rounded-full ${DOT[tone]}`} />}
            {value ?? '—'}
          </div>
          {detail && <div className="mt-1 truncate text-xs text-gray-500">{detail}</div>}
        </div>
      )}
    </div>
  )
}
