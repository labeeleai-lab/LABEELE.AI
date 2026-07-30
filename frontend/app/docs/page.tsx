import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

const ENDPOINTS = [
  { method: 'POST', path: '/agency/dispatch', description: 'Send a prompt to DUKE and get routed to the best-matching persona automatically.' },
  { method: 'POST', path: '/tasks/submit', description: 'Submit a task to a specific DUKE persona by id, with a complexity score (1-10).' },
  { method: 'GET', path: '/agents', description: 'List DUKE’s live specialist personas and their current status.' },
  { method: 'GET', path: '/model/status', description: 'Check whether DUKE is ready or still training.' },
  { method: 'GET', path: '/health', description: 'Basic service health check.' },
]

export default function DocsPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl font-bold text-white mb-4">Getting started with DUKE</h1>
            <p className="text-lg text-gray-400 mb-12">
              DUKE is the single controller model behind LABEELE.AI &mdash; it&apos;s used from the
              dashboard&apos;s query interface after you sign up, no API key management needed. This
              page documents what&apos;s happening under the hood for anyone integrating directly.
            </p>

            <GlassCard className="mb-10">
              <h2 className="text-xl font-semibold text-white mb-4">1. Create an account</h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                Sign up for free &mdash; every plan includes a 14-day trial with no credit card required.
              </p>
            </GlassCard>

            <GlassCard className="mb-10">
              <h2 className="text-xl font-semibold text-white mb-4">2. Choose a persona, or let DUKE pick</h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                From the dashboard, pick one of DUKE&apos;s seven live personas &mdash; security, ML,
                systems, backend, DevOps, vision, or emerging tech &mdash; or describe your task and
                let DUKE route it to the persona best suited to it automatically.
              </p>
            </GlassCard>

            <GlassCard className="mb-16">
              <h2 className="text-xl font-semibold text-white mb-4">3. Send your query</h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                Responses come from DUKE&apos;s locally-run model, so a query can take up to a minute
                to complete, especially the first one after the service has been idle.
              </p>
            </GlassCard>

            <h2 className="text-2xl font-bold text-white mb-6">API reference</h2>
            <p className="text-gray-400 mb-8">
              Core endpoints exposed by DUKE&apos;s backend service. All are unauthenticated at the
              network level &mdash; access control happens at the application layer.
            </p>

            <div className="space-y-4">
              {ENDPOINTS.map((endpoint) => (
                <GlassCard key={endpoint.path}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-bold px-2 py-1 rounded bg-gold-500/15 text-gold-500">
                      {endpoint.method}
                    </span>
                    <code className="text-sm text-white font-mono">{endpoint.path}</code>
                  </div>
                  <p className="text-gray-400 text-sm">{endpoint.description}</p>
                </GlassCard>
              ))}
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
