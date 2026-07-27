import Link from 'next/link'
import { Check } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

const TIERS = [
  {
    name: 'Starter',
    price: '99',
    description: 'For individuals and small teams getting started',
    features: [
      'Up to 3 specialist agents',
      '10,000 queries / month',
      'Basic usage dashboard',
      'Email support',
    ],
    cta: { label: 'Start free trial', href: '/signup' },
  },
  {
    name: 'Professional',
    price: '299',
    description: 'For growing teams that need every specialist',
    features: [
      'All 6 specialist agents',
      '100,000 queries / month',
      'Advanced usage dashboard',
      'Priority support',
      'Custom integrations',
    ],
    cta: { label: 'Start free trial', href: '/signup' },
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For large-scale or dedicated deployments',
    features: [
      'Unlimited agents & queries',
      'Dedicated infrastructure',
      'Custom SLA agreements',
      '24/7 priority support',
    ],
    cta: { label: 'Contact sales', href: '/contact' },
  },
]

export default function PricingPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto text-center mb-16">
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4">Simple, transparent pricing</h1>
            <p className="text-lg text-gray-400">
              Every plan includes a 14-day free trial. No credit card required to start.
            </p>
          </div>

          <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`bg-white/5 backdrop-blur-md border rounded-xl p-8 flex flex-col ${
                  tier.popular ? 'border-gold-500 shadow-lg shadow-gold-500/10' : 'border-gold-500/20'
                }`}
              >
                {tier.popular && (
                  <div className="self-start mb-4 px-3 py-1 rounded-full bg-gold-500 text-royal-blue-900 text-xs font-bold uppercase tracking-wide">
                    Most popular
                  </div>
                )}
                <h2 className="text-xl font-semibold text-white mb-1">{tier.name}</h2>
                <p className="text-gray-400 text-sm mb-6">{tier.description}</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-white">
                    {tier.price === 'Custom' ? tier.price : `$${tier.price}`}
                  </span>
                  {tier.price !== 'Custom' && <span className="text-gray-400"> /month</span>}
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm text-gray-300">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link
                  href={tier.cta.href}
                  className={`block text-center px-5 py-3 rounded-lg font-semibold transition-colors ${
                    tier.popular
                      ? 'bg-gold-500 text-royal-blue-900 hover:bg-gold-400'
                      : 'border border-gold-500/40 text-gold-500 hover:bg-gold-500/10'
                  }`}
                >
                  {tier.cta.label}
                </Link>
              </div>
            ))}
          </div>

          <div className="max-w-2xl mx-auto text-center mt-16">
            <p className="text-gray-400 text-sm">
              Need something in between? <Link href="/contact" className="text-gold-500 hover:text-gold-400">Talk to us</Link> about a custom plan.
            </p>
          </div>
        </section>

        <section className="px-6 lg:px-8 py-20 border-t border-gold-500/10">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-8 text-center">Frequently asked questions</h2>
            <div className="space-y-6">
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">What counts as a query?</h3>
                <p className="text-gray-400 text-sm">One request to a specialist agent, whether it&apos;s routed automatically or chosen directly.</p>
              </GlassCard>
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Can I change plans later?</h3>
                <p className="text-gray-400 text-sm">Yes, upgrade or downgrade at any time from your account settings.</p>
              </GlassCard>
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Is there a free trial?</h3>
                <p className="text-gray-400 text-sm">Every plan starts with a 14-day free trial, no credit card required.</p>
              </GlassCard>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
