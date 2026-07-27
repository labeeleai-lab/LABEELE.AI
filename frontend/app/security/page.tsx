import { Lock, ShieldCheck, KeyRound, Server } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

const PRACTICES = [
  {
    icon: KeyRound,
    title: 'Authentication',
    description: 'Accounts and sessions are handled by Supabase Auth, with hashed credentials and email verification on signup.',
  },
  {
    icon: Lock,
    title: 'Encryption in transit',
    description: 'All traffic between your browser, the application, and the backend is served over HTTPS.',
  },
  {
    icon: ShieldCheck,
    title: 'Access control',
    description: 'The product dashboard and account data are only reachable once you\'re signed in - protected routes are enforced server-side, not just hidden in the UI.',
  },
  {
    icon: Server,
    title: 'Data storage',
    description: 'Account and application data is stored with Supabase; query processing is handled by our dedicated backend service.',
  },
]

export default function SecurityPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl font-bold text-white mb-4">Security</h1>
            <p className="text-lg text-gray-400 mb-12">
              We build around established security practices rather than rolling our own. Here&apos;s
              what that looks like in practice.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-12">
              {PRACTICES.map((practice) => {
                const Icon = practice.icon
                return (
                  <GlassCard key={practice.title}>
                    <Icon className="w-6 h-6 text-gold-500 mb-3" />
                    <h3 className="font-semibold text-white mb-2">{practice.title}</h3>
                    <p className="text-gray-400 text-sm leading-relaxed">{practice.description}</p>
                  </GlassCard>
                )
              })}
            </div>

            <GlassCard>
              <h3 className="font-semibold text-white mb-2">Found a security issue?</h3>
              <p className="text-gray-400 text-sm">
                Please report it to{' '}
                <a href="mailto:security@labeele.ai" className="text-gold-500 hover:text-gold-400">
                  security@labeele.ai
                </a>{' '}
                &mdash; we take reports seriously and will respond promptly.
              </p>
            </GlassCard>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
