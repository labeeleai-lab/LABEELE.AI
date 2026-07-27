import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

export default function AboutPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-6">About LABEELE.AI</h1>
            <p className="text-lg text-gray-300 leading-relaxed mb-6">
              Most AI products ask one general-purpose model to be an expert at everything. We
              think that trade-off shows up in the answers &mdash; a single model spreads its
              attention across security, ML, infrastructure, code, operations, and vision all at
              once.
            </p>
            <p className="text-lg text-gray-300 leading-relaxed mb-12">
              LABEELE.AI is built around DUKE, a single model that acts as a controller rather
              than a generalist &mdash; it identifies the task in front of it and injects the
              specialist persona best suited to solve it, routed automatically or chosen
              directly. The goal is answers that read like they came from someone who actually
              works in that field, and a system that keeps growing every time DUKE learns a new
              persona.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Focused, not generic</h3>
                <p className="text-gray-400 text-sm">Each specialist is scoped to one domain instead of trying to cover everything.</p>
              </GlassCard>
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Built to be used daily</h3>
                <p className="text-gray-400 text-sm">A real product with real accounts, not a demo or a one-off script.</p>
              </GlassCard>
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Honest about limits</h3>
                <p className="text-gray-400 text-sm">Responses come from a real backend model, not a scripted mock &mdash; and we say so when something isn&apos;t ready yet.</p>
              </GlassCard>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
