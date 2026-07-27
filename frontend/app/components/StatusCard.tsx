import { Loader2, AlertTriangle } from 'lucide-react'
import GlassCard from './GlassCard'

export default function StatusCard({
  label,
  value,
  detail,
  loading,
  error,
}: {
  label: string
  value?: string
  detail?: string
  loading: boolean
  error?: string | null
}) {
  return (
    <GlassCard>
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">{label}</div>
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
