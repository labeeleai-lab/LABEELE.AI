import Link from 'next/link'
import {
  Brain,
  Eye,
  Shield,
  Server,
  Code2,
  Rocket,
  Globe,
  MessageSquare,
  Network,
  AudioLines,
  ArrowRight,
  Check,
  Clock,
  DollarSign,
} from 'lucide-react'
import SiteHeader from './components/SiteHeader'
import SiteFooter from './components/SiteFooter'
import GlassCard from './components/GlassCard'

const LIVE_PERSONAS = [
  { icon: Shield, name: 'Security Specialist', description: 'Threat modeling, vulnerability triage, zero-trust hardening.' },
  { icon: Brain, name: 'Machine Learning Theorist', description: 'Model architecture, training strategy, evaluation design.' },
  { icon: Server, name: 'System Architect', description: 'Cloud architecture, scalability, fault tolerance, cost.' },
  { icon: Code2, name: 'Backend Developer', description: 'API design, data layer decisions, resilience patterns.' },
  { icon: Rocket, name: 'DevOps', description: 'CI/CD pipelines, infrastructure as code, release strategy.' },
  { icon: Eye, name: 'Vision Specialist', description: 'Object recognition, composition, spatial reasoning.' },
]

const ROADMAP_PERSONAS = [
  { icon: Globe, name: 'Web Developer' },
  { icon: MessageSquare, name: 'Prompt Engineer' },
  { icon: Network, name: 'Architect Vision Node' },
  { icon: AudioLines, name: 'Audio Voice Scrambler (AVS)' },
]

const METRICS = [
  { value: '6', label: 'Personas live today' },
  { value: '24/7', label: 'Availability' },
  { value: '1', label: 'Brain, one interface' },
  { value: '0', label: 'Setup required' },
]

export default function HomePage() {
  return (
    <>
      <SiteHeader />

      <main className="bg-royal-blue-900">
        {/* Hero */}
        <section className="relative px-6 lg:px-8 py-24 lg:py-32 overflow-hidden">
          <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative z-10">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 border border-gold-500/40 text-gold-500 px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide">
                Powered by DUKE
              </div>

              <h1 className="text-4xl lg:text-6xl font-bold text-white leading-[1.1] tracking-tight">
                One AI brain.
                <br />
                <span className="text-gold-500">Every specialist skill.</span>
              </h1>

              <p className="text-lg text-gray-300 leading-relaxed max-w-xl">
                DUKE is the model behind LABEELE.AI &mdash; a single controller that routes every
                request to the right specialist persona, in place of coordinating a team of
                human specialists for the same work.
              </p>

              <div className="flex flex-wrap gap-4 pt-2">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 px-6 py-3.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors"
                >
                  Start free trial
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/features"
                  className="inline-flex items-center gap-2 px-6 py-3.5 border border-gold-500/40 text-gold-500 font-semibold rounded-lg hover:bg-gold-500/10 transition-colors"
                >
                  Meet DUKE
                </Link>
              </div>

              <div className="flex items-center gap-6 pt-2 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span>No credit card required</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span>14-day free trial</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {METRICS.map((metric) => (
                <GlassCard key={metric.label}>
                  <div className="text-3xl font-bold text-gold-500 mb-1">{metric.value}</div>
                  <div className="text-sm text-gray-400">{metric.label}</div>
                </GlassCard>
              ))}
            </div>
          </div>
        </section>

        {/* Meet DUKE */}
        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-6">Meet DUKE</h2>
              <p className="text-lg text-gray-300 leading-relaxed mb-5">
                DUKE isn&apos;t six separate AI products bundled together. It&apos;s one brain with a
                growing library of specialist personas &mdash; skills DUKE draws on the way a person
                draws on specific expertise for a specific job. When your request comes in, DUKE
                identifies what kind of problem it is and injects the persona best suited to solve
                it.
              </p>
              <p className="text-lg text-gray-300 leading-relaxed mb-8">
                Every new persona DUKE learns expands what the whole system can do. It&apos;s built to
                keep growing, not to ship once and stay fixed.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-gold-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-white font-semibold text-sm">Faster resolution</div>
                    <div className="text-gray-400 text-sm">No hand-offs between specialists or vendors.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <DollarSign className="w-5 h-5 text-gold-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-white font-semibold text-sm">Lower cost</div>
                    <div className="text-gray-400 text-sm">One system in place of a team of specialist hires.</div>
                  </div>
                </div>
              </div>
            </div>

            <GlassCard className="p-10">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-gold-500 flex items-center justify-center mb-4">
                  <Brain className="w-8 h-8 text-royal-blue-900" />
                </div>
                <div className="text-xl font-bold text-white mb-1">DUKE</div>
                <div className="text-sm text-gray-400 mb-8">The controller - routes every task</div>

                <div className="grid grid-cols-3 gap-3 w-full">
                  {LIVE_PERSONAS.map((persona) => {
                    const Icon = persona.icon
                    return (
                      <div
                        key={persona.name}
                        className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-white/5 border border-gold-500/15"
                        title={persona.name}
                      >
                        <Icon className="w-4 h-4 text-gold-500" />
                      </div>
                    )
                  })}
                </div>
                <p className="text-xs text-gray-500 mt-4">DUKE&apos;s six live specialist personas</p>
              </div>
            </GlassCard>
          </div>
        </section>

        {/* Live personas */}
        <section id="features" className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-2xl mb-16">
              <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold uppercase tracking-wide">
                Live today
              </div>
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">DUKE&apos;s current personas</h2>
              <p className="text-lg text-gray-400">
                Each persona is scoped to a domain, so answers read like they came from someone who
                actually works in that field.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {LIVE_PERSONAS.map((persona) => {
                const Icon = persona.icon
                return (
                  <GlassCard key={persona.name}>
                    <Icon className="w-7 h-7 text-gold-500 mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">{persona.name}</h3>
                    <p className="text-gray-400 text-sm leading-relaxed">{persona.description}</p>
                  </GlassCard>
                )
              })}
            </div>

            <div className="mt-16 pt-16 border-t border-gold-500/10">
              <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/30 text-gold-500 text-xs font-semibold uppercase tracking-wide">
                Expanding next
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">More sectors in active development</h3>
              <p className="text-gray-400 mb-8 max-w-2xl">
                These personas are part of the roadmap and not yet queryable in the live product.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {ROADMAP_PERSONAS.map((persona) => {
                  const Icon = persona.icon
                  return (
                    <div
                      key={persona.name}
                      className="flex flex-col items-center text-center gap-2 p-5 rounded-xl border border-dashed border-gold-500/25 text-gray-400"
                    >
                      <Icon className="w-6 h-6 text-gold-500/70" />
                      <span className="text-sm font-medium">{persona.name}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="mt-10">
              <Link href="/features" className="inline-flex items-center gap-2 text-gold-500 font-medium hover:text-gold-400 transition-colors">
                See every capability <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-2xl mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Get started in three steps</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { step: '01', title: 'Create an account', description: 'Sign up and get instant access to the dashboard - no setup or configuration needed.' },
                { step: '02', title: 'Ask DUKE', description: 'Describe your task and DUKE routes it to the right persona, or pick one directly.' },
                { step: '03', title: 'Get a focused answer', description: 'Get a domain-specific response back, from the specialist DUKE selected for the job.' },
              ].map((item) => (
                <GlassCard key={item.step}>
                  <div className="text-4xl font-bold text-gold-500/25 mb-3">{item.step}</div>
                  <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{item.description}</p>
                </GlassCard>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing teaser */}
        <section id="pricing" className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Simple, transparent pricing</h2>
            <p className="text-lg text-gray-400 mb-8">
              Every plan includes a 14-day free trial. See the full breakdown of what&apos;s included.
            </p>
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 px-6 py-3.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors"
            >
              View pricing <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>

        {/* CTA */}
        <section className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-4xl mx-auto text-center">
            <GlassCard className="p-12">
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                Ready to put DUKE to work?
              </h2>
              <p className="text-lg text-gray-300 mb-8">
                Start a free trial and get an answer from a real specialist persona in minutes.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors"
                >
                  Start free trial <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/contact"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 border border-gold-500/40 text-gold-500 font-semibold rounded-lg hover:bg-gold-500/10 transition-colors"
                >
                  Contact sales
                </Link>
              </div>
            </GlassCard>
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  )
}
