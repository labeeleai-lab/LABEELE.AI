import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

export default function CompliancePage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl font-bold text-white mb-4">Compliance</h1>
            <p className="text-lg text-gray-400 mb-12">
              We&apos;re a small, growing product. Here&apos;s an honest picture of where we stand today.
            </p>

            <div className="space-y-6">
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Today</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  We follow SOC 2-aligned practices in how we handle authentication, access
                  control, and data storage (via Supabase), but we have not completed a formal SOC 2,
                  ISO 27001, or HIPAA audit yet.
                </p>
              </GlassCard>
              <GlassCard>
                <h3 className="font-semibold text-white mb-2">Working toward</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  As we grow, we plan to pursue formal certifications relevant to our customers.
                  If your organization has specific compliance requirements, let us know at{' '}
                  <a href="mailto:compliance@labeele.ai" className="text-gold-500 hover:text-gold-400">
                    compliance@labeele.ai
                  </a>{' '}
                  and we&apos;ll tell you where we stand against them.
                </p>
              </GlassCard>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
