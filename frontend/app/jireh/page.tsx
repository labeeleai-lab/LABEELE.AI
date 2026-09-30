'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { GraduationCap, Users2, ClipboardList, Code2, ArrowRight, BookOpen, Mail, Users } from 'lucide-react'
import AdminShell from '../components/AdminShell'
import { PageHeader } from '../components/ui'
import StatusCard from '../components/StatusCard'
import {
  dukeApi,
  DukeApiError,
  type HealthStatus,
  type ModelStatus,
  type LearningStatus,
  type IacStats,
} from '@/lib/duke-api'

function useFetch<T>(fn: () => Promise<T>) {
  const [state, setState] = useState<{ data?: T; loading: boolean; error?: string }>({ loading: true })

  useEffect(() => {
    let cancelled = false
    fn().then(
      (data) => !cancelled && setState({ data, loading: false }),
      (err) => !cancelled && setState({ loading: false, error: err instanceof DukeApiError ? err.message : 'Unreachable' }),
    )
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return state
}

const SECTIONS = [
  { href: '/jireh/training', icon: GraduationCap, title: 'Training', group: 'Model', description: "Fine-tune DUKE's answer model on curated data and track each run." },
  { href: '/jireh/personas', icon: Users2, title: 'Personas', group: 'Model', description: "Edit DUKE's personas at runtime, or create new ones." },
  { href: '/jireh/knowledge', icon: BookOpen, title: 'Knowledge', group: 'Model', description: 'Documents each persona retrieves from live when answering.' },
  { href: '/jireh/annotate', icon: ClipboardList, title: 'Annotate', group: 'Model', description: 'Review recent queries and rate or correct responses.' },
  { href: '/jireh/code', icon: Code2, title: 'Code', group: 'Workspace', description: 'Browse, edit, and commit repo files via GitHub.' },
  { href: '/jireh/messages', icon: Mail, title: 'Messages', group: 'Workspace', description: 'Contact-form messages sent from the public site.' },
  { href: '/jireh/team', icon: Users, title: 'Team', group: 'Workspace', description: 'Manage who has JIREH admin access.' },
]

export default function AdminOverviewPage() {
  const health = useFetch<HealthStatus>(() => dukeApi.health())
  const model = useFetch<ModelStatus>(() => dukeApi.modelStatus())
  const learning = useFetch<LearningStatus>(() => dukeApi.learningStatus())
  const iac = useFetch<IacStats>(() => dukeApi.iacStats())

  const online = health.data?.status === 'ok'

  return (
    <AdminShell>
      <PageHeader
        eyebrow="JIREH · Model operations"
        title="Overview"
        description="Live status of the DUKE backend, and every control for training, tuning, and grounding its answers."
      />

      <section aria-label="System status" className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard
          label="Backend"
          loading={health.loading}
          error={health.error}
          value={online ? 'Online' : health.data?.status}
          tone={online ? 'good' : 'warn'}
          detail={health.data?.service}
        />
        <StatusCard
          label="Model"
          loading={model.loading}
          error={model.error}
          value={model.data?.status === 'ready' ? 'Ready' : 'Training'}
          tone={model.data?.status === 'ready' ? 'good' : 'warn'}
          detail={model.data?.version ? `v${model.data.version}` : undefined}
        />
        <StatusCard
          label="Specialists"
          loading={learning.loading}
          error={learning.error}
          value={learning.data ? String(learning.data.agent_personas?.length ?? 0) : undefined}
          detail={learning.data ? `${learning.data.total_inferences ?? 0} total queries` : undefined}
        />
        <StatusCard
          label="IAC validated"
          loading={iac.loading}
          error={iac.error}
          value={iac.data ? `${iac.data.validated}/${iac.data.total}` : undefined}
          detail="Adversarial-validated training samples"
        />
      </section>

      {(['Model', 'Workspace'] as const).map((group) => (
        <section key={group} aria-labelledby={`jireh-${group}`} className="mb-8">
          <h2 id={`jireh-${group}`} className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">
            {group}
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {SECTIONS.filter((s) => s.group === group).map((section) => {
              const Icon = section.icon
              return (
                <Link key={section.href} href={section.href} className="surface surface-interactive group flex flex-col p-5">
                  <span className="mb-4 grid h-9 w-9 place-items-center rounded-lg border border-gold-500/30 bg-gold-500/10 text-gold-400">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="flex items-center gap-1.5 font-semibold text-white">
                    {section.title}
                    <ArrowRight className="h-3.5 w-3.5 -translate-x-1 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100" aria-hidden="true" />
                  </span>
                  <span className="mt-1 text-sm leading-relaxed text-gray-400">{section.description}</span>
                </Link>
              )
            })}
          </div>
        </section>
      ))}
    </AdminShell>
  )
}
