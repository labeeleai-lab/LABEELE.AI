import { Loader2, AlertTriangle, Info } from 'lucide-react'
import GlassCard from './GlassCard'

export function HintIcon({ text }: { text: string }) {
  return (
    <span className="relative inline-flex group/hint normal-case tracking-normal font-normal align-middle">
      <Info className="w-3 h-3 text-gray-500 hover:text-gray-300 cursor-help" />
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-56 rounded-lg
          border border-gold-500/30 bg-[#0f1729] px-3 py-2 text-xs leading-relaxed text-gray-300 opacity-0
          shadow-xl transition-opacity duration-150 group-hover/hint:opacity-100 group-focus/hint:opacity-100 z-20"
      >
        {text}
      </span>
    </span>
  )
}

export default function StatusCard({
  label,
  value,
  detail,
  loading,
  error,
  hint,
}: {
  label: string
  value?: string
  detail?: string
  loading: boolean
  error?: string | null
  hint?: string
}) {
  return (
    <GlassCard>
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
        {label}
        {hint && <HintIcon text={hint} />}
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Checking&hellip;</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-amber-400" title={error}>
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">Offline</span>
        </div>
      ) : (
        <>
          <div className="text-xl font-bold text-white">{value}</div>
          {detail && <div className="text-xs text-gray-500 mt-1">{detail}</div>}
        </>
      )}
    </GlassCard>
  )
}
