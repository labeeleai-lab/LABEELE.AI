import Link from 'next/link'
import { Brain, Eye, Shield, Activity, Users, ArrowRight, Check } from 'lucide-react'
import SiteHeader from './components/SiteHeader'
import SiteFooter from './components/SiteFooter'
import GlassCard from './components/GlassCard'

const CAPABILITIES = [
  {
    icon: Brain,
    title: 'ML expertise on demand',
    description: 'A specialist trained on model architecture, training strategy, and evaluation - ask it to reason through a real ML problem.',
  },
  {
    icon: Eye,
    title: 'Vision analysis',
    description: 'Detailed visual reasoning about objects, composition, and spatial relationships from a dedicated vision specialist.',
  },
  {
    icon: Shield,
    title: 'Security-first design',
    description: 'A security architect persona for threat modeling, vulnerability triage, and hardening guidance, built around zero-trust principles.',
  },
  {
    icon: Activity,
    title: 'Systems & infrastructure',
    description: 'Cloud architecture, scaling strategy, and reliability guidance from a dedicated infrastructure specialist.',
  },
  {
    icon: Users,
    title: '6 specialist personas',
    description: 'Security, ML, systems, backend, DevOps, and vision - each a focused expert rather than one generic assistant.',
  },
]

const METRICS = [
  { value: '6', label: 'Specialist agents' },
  { value: '24/7', label: 'Availability' },
  { value: '1', label: 'Query interface' },
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
                Specialist AI Agents
              </div>

              <h1 className="text-4xl lg:text-6xl font-bold text-white leading-[1.1] tracking-tight">
                Six AI specialists.
                <br />
                <span className="text-gold-500">One query interface.</span>
              </h1>

              <p className="text-lg text-gray-300 leading-relaxed max-w-xl">
                LABEELE.AI routes your question to a focused specialist &mdash; security, ML, systems,
                backend, DevOps, or vision &mdash; instead of one generic model guessing at all of them.
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
                  See how it works
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

        {/* Capabilities */}
        <section id="features" className="px-6 lg:px-8 py-24 border-t border-gold-500/10">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-2xl mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">Built around specialists, not one generalist</h2>
              <p className="text-lg text-gray-400">
                Each persona is scoped to a domain, so answers read like they came from someone who
                actually works in that field.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {CAPABILITIES.map((feature) => {
                const Icon = feature.icon
                return (
                  <GlassCard key={feature.title}>
                    <Icon className="w-7 h-7 text-gold-500 mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                    <p className="text-gray-400 text-sm leading-relaxed">{feature.description}</p>
                  </GlassCard>
                )
              })}
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
                { step: '02', title: 'Pick a specialist', description: 'Choose the persona that fits your task, or let it default to the most relevant one.' },
                { step: '03', title: 'Ask your question', description: 'Send your query and get a focused, domain-specific response back.' },
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
                Ready to try LABEELE.AI?
              </h2>
              <p className="text-lg text-gray-300 mb-8">
                Start a free trial and get an answer from a real specialist in minutes.
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
