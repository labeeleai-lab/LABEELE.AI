import Link from 'next/link'
import { Newspaper } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

export default function BlogPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-2xl mx-auto text-center">
            <h1 className="text-4xl font-bold text-white mb-4">Blog</h1>
            <GlassCard className="mt-10">
              <div className="flex flex-col items-center gap-4 py-8">
                <Newspaper className="w-10 h-10 text-gold-500/60" />
                <h2 className="text-xl font-semibold text-white">Nothing published yet</h2>
                <p className="text-gray-400 text-sm max-w-sm">
                  We&apos;re focused on the product right now. Check back soon, or{' '}
                  <Link href="/contact" className="text-gold-500 hover:text-gold-400">
                    get in touch
                  </Link>{' '}
                  if you have something you&apos;d like us to write about.
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
