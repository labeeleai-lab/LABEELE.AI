import Link from 'next/link'
import { Shield, Brain, Server, Code2, Rocket, Eye, ArrowRight } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

const AGENTS = [
  {
    icon: Shield,
    name: 'Security Expert',
    category: 'Security',
    description: 'Threat modeling, vulnerability triage, and hardening guidance built around zero-trust principles - attack surface, mitigation strategy, and monitoring requirements.',
  },
  {
    icon: Brain,
    name: 'ML Expert',
    category: 'Machine Learning',
    description: 'Problem formalization, data strategy, model architecture, and evaluation design for real machine learning problems.',
  },
  {
    icon: Server,
    name: 'Systems Expert',
    category: 'Infrastructure',
    description: 'Cloud architecture, scalability strategy, fault tolerance, and cost optimization for distributed systems.',
  },
  {
    icon: Code2,
    name: 'Backend Expert',
    category: 'Software Engineering',
    description: 'API design, data layer decisions, resilience patterns, and testing strategy for backend services.',
  },
  {
    icon: Rocket,
    name: 'DevOps Expert',
    category: 'DevOps',
    description: 'CI/CD pipeline design, infrastructure as code, container orchestration, and release strategy.',
  },
  {
    icon: Eye,
    name: 'Vision Expert',
    category: 'Computer Vision',
    description: 'Detailed visual analysis - object recognition, composition, spatial relationships, and lighting.',
  },
]

export default function FeaturesPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-4xl mx-auto text-center mb-16">
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">
              Six specialists, one interface
            </h1>
            <p className="text-lg text-gray-400">
              Every query goes to a persona scoped to a specific domain, not a single model
              trying to be everything at once.
            </p>
          </div>

          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {AGENTS.map((agent) => {
              const Icon = agent.icon
              return (
                <GlassCard key={agent.name}>
                  <Icon className="w-7 h-7 text-gold-500 mb-4" />
                  <div className="text-xs font-semibold uppercase tracking-wide text-gold-500/80 mb-1">
                    {agent.category}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{agent.name}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{agent.description}</p>
                </GlassCard>
              )
            })}
          </div>
        </section>

        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold text-white mb-4">How routing works</h2>
            <p className="text-gray-400 mb-8">
              Pick a specialist directly from the dashboard, or describe your task and let the
              router match it to the closest fit automatically.
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-6 py-3.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors"
            >
              Try it free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
