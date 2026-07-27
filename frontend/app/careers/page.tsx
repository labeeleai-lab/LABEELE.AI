import Link from 'next/link'
import { Briefcase } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

export default function CareersPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-2xl mx-auto text-center">
            <h1 className="text-4xl font-bold text-white mb-4">Careers</h1>
            <GlassCard className="mt-10">
              <div className="flex flex-col items-center gap-4 py-8">
                <Briefcase className="w-10 h-10 text-gold-500/60" />
                <h2 className="text-xl font-semibold text-white">No open roles right now</h2>
                <p className="text-gray-400 text-sm max-w-sm">
                  We&apos;re a small team today. If that changes, we&apos;ll post roles here &mdash; in the
                  meantime, feel free to{' '}
                  <Link href="/contact" className="text-gold-500 hover:text-gold-400">
                    reach out
                  </Link>{' '}
                  and introduce yourself.
                </p>
              </div>
            </GlassCard>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
