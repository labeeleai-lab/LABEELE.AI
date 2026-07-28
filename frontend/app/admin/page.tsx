'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { GraduationCap, Users2, ClipboardList, Code2, ArrowRight, BookOpen } from 'lucide-react'
import AdminShell from '../components/AdminShell'
import GlassCard from '../components/GlassCard'
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
  { href: '/admin/training', icon: GraduationCap, title: 'Training', description: 'Trigger retraining, clear the training cache, view stats.' },
  { href: '/admin/personas', icon: Users2, title: 'Personas', description: "Edit DUKE's personas at runtime, or create new ones." },
  { href: '/admin/knowledge', icon: BookOpen, title: 'Knowledge', description: 'Train DUKE or any agent with documents - retrieved live in real responses.' },
  { href: '/admin/annotate', icon: ClipboardList, title: 'Annotate', description: 'Review recent queries and rate/correct responses.' },
  { href: '/admin/code', icon: Code2, title: 'Code', description: 'Browse, edit, and commit repo files via GitHub.' },
]

export default function AdminOverviewPage() {
  const health = useFetch<HealthStatus>(() => dukeApi.health())
  const model = useFetch<ModelStatus>(() => dukeApi.modelStatus())
  const learning = useFetch<LearningStatus>(() => dukeApi.learningStatus())
  const iac = useFetch<IacStats>(() => dukeApi.iacStats())

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Admin overview</h1>
      <p className="text-gray-400 mb-8">Live status of the DUKE backend.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatusCard
          label="Backend"
          loading={health.loading}
          error={health.error}
          value={health.data?.status === 'ok' ? 'Online' : health.data?.status}
          detail={health.data?.service}
        />
        <StatusCard
          label="Model"
          loading={model.loading}
          error={model.error}
          value={model.data?.status === 'ready' ? 'Ready' : 'Training'}
          detail={model.data?.version ? `v${model.data.version}` : undefined}
        />
        <StatusCard
          label="Specialists"
          loading={learning.loading}
          error={learning.error}
          value={learning.data ? String(learning.data.agent_personas.length) : undefined}
          detail={learning.data ? `${learning.data.total_inferences} total queries` : undefined}
        />
        <StatusCard
          label="IAC validated"
          loading={iac.loading}
          error={iac.error}
          value={iac.data ? `${iac.data.validated}/${iac.data.total}` : undefined}
          detail="Adversarial-validated training samples"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {SECTIONS.map((section) => {
          const Icon = section.icon
          return (
            <Link key={section.href} href={section.href}>
              <GlassCard className="h-full group">
                <Icon className="w-6 h-6 text-gold-500 mb-3" />
                <h3 className="font-semibold text-white mb-1.5 flex items-center gap-1.5">
                  {section.title}
                  <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </h3>
                <p className="text-gray-400 text-sm">{section.description}</p>
              </GlassCard>
            </Link>
          )
        })}
      </div>
    </AdminShell>
  )
}
