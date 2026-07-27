import Link from 'next/link'
import { Shield, Brain, Server, Code2, Rocket, Eye, Globe, MessageSquare, Network, AudioLines, ArrowRight } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

const LIVE_PERSONAS = [
  {
    icon: Shield,
    name: 'Security Specialist',
    category: 'Security',
    description: 'Threat modeling, vulnerability triage, and hardening guidance built around zero-trust principles - attack surface, mitigation strategy, and monitoring requirements.',
  },
  {
    icon: Brain,
    name: 'Machine Learning Theorist',
    category: 'Machine Learning',
    description: 'Problem formalization, data strategy, model architecture, and evaluation design for real machine learning problems.',
  },
  {
    icon: Server,
    name: 'System Architect',
    category: 'Infrastructure',
    description: 'Cloud architecture, scalability strategy, fault tolerance, and cost optimization for distributed systems.',
  },
  {
    icon: Code2,
    name: 'Backend Developer',
    category: 'Software Engineering',
    description: 'API design, data layer decisions, resilience patterns, and testing strategy for backend services.',
  },
  {
    icon: Rocket,
    name: 'DevOps',
    category: 'DevOps',
    description: 'CI/CD pipeline design, infrastructure as code, container orchestration, and release strategy.',
  },
  {
    icon: Eye,
    name: 'Vision Specialist',
    category: 'Computer Vision',
    description: 'Detailed visual analysis - object recognition, composition, spatial relationships, and lighting.',
  },
]

const ROADMAP_PERSONAS = [
  { icon: Globe, name: 'Web Developer', description: 'Building and reasoning about front-end interfaces and web applications.' },
  { icon: MessageSquare, name: 'Prompt Engineer', description: 'Designing and refining prompts and instructions for other AI systems.' },
  { icon: Network, name: 'Architect Vision Node', description: 'Coordinating vision-based reasoning across distributed inputs.' },
  { icon: AudioLines, name: 'Audio Voice Scrambler (AVS)', description: 'Audio and voice processing capabilities.' },
]

export default function FeaturesPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-4xl mx-auto text-center mb-16">
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">
              One brain. A growing set of specialist personas.
            </h1>
            <p className="text-lg text-gray-400">
              DUKE is the single model behind LABEELE.AI. Rather than one generic assistant
              guessing at every domain, DUKE identifies the task and injects the specialist
              persona best suited to it &mdash; the way a person draws on a specific skill for a
              specific job.
            </p>
          </div>

          <div className="max-w-2xl mx-auto text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold uppercase tracking-wide">
              Live today
            </div>
          </div>

          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {LIVE_PERSONAS.map((persona) => {
              const Icon = persona.icon
              return (
                <GlassCard key={persona.name}>
                  <Icon className="w-7 h-7 text-gold-500 mb-4" />
                  <div className="text-xs font-semibold uppercase tracking-wide text-gold-500/80 mb-1">
                    {persona.category}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{persona.name}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{persona.description}</p>
                </GlassCard>
              )
            })}
          </div>
        </section>

        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-2xl mb-10">
              <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/30 text-gold-500 text-xs font-semibold uppercase tracking-wide">
                Expanding next
              </div>
              <h2 className="text-3xl font-bold text-white mb-3">DUKE keeps learning new sectors</h2>
              <p className="text-gray-400">
                These personas are on the roadmap and not yet queryable in the live product. Every
                new persona DUKE learns expands what the whole system can do.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {ROADMAP_PERSONAS.map((persona) => {
                const Icon = persona.icon
                return (
                  <div
                    key={persona.name}
                    className="p-5 rounded-xl border border-dashed border-gold-500/25"
                  >
                    <Icon className="w-6 h-6 text-gold-500/70 mb-3" />
                    <h3 className="text-sm font-semibold text-gray-300 mb-1.5">{persona.name}</h3>
                    <p className="text-gray-500 text-xs leading-relaxed">{persona.description}</p>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold text-white mb-4">How routing works</h2>
            <p className="text-gray-400 mb-8">
              Pick a persona directly from the dashboard, or describe your task and let DUKE match
              it to the closest fit automatically.
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
