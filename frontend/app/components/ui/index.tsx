import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle, type LucideIcon } from 'lucide-react'

// Shared LABEELE.AI UI primitives. Styling lives in globals.css
// (.surface*, .btn*, .input, .alert*, .badge*, .eyebrow) so plain elements
// can use the same system via className without a wrapper component.

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className = '',
}: {
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <header className={`mb-8 flex flex-wrap items-end justify-between gap-4 ${className}`}>
      <div className="min-w-0 max-w-3xl">
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 text-[15px] leading-relaxed text-gray-400">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function SectionTitle({ children, description, actions }: { children: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-white">{children}</h2>
        {description && <p className="mt-1 text-sm text-gray-400">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

type AlertTone = 'success' | 'error' | 'warning' | 'info'
const ALERT_ICONS: Record<AlertTone, LucideIcon> = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

export function Alert({ tone, children, className = '' }: { tone: AlertTone; children: ReactNode; className?: string }) {
  const Icon = ALERT_ICONS[tone]
  return (
    <div role={tone === 'error' || tone === 'warning' ? 'alert' : 'status'} className={`alert alert-${tone} ${className}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 break-words">{children}</div>
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className = '',
}: {
  icon: LucideIcon
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-col items-center px-4 py-10 text-center ${className}`}>
      <span className="mb-3 grid h-11 w-11 place-items-center rounded-xl border border-white/10 bg-white/[0.04] text-gray-400">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <p className="text-sm font-semibold text-gray-100">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-gray-400">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function LoadingRow({ label = 'Loading…', className = '' }: { label?: string; className?: string }) {
  return (
    <div role="status" className={`flex items-center gap-2 py-3 text-sm text-gray-400 ${className}`}>
      <Loader2 className="h-4 w-4 animate-spin text-gold-500" aria-hidden="true" />
      {label}
    </div>
  )
}
