import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'

export default function PrivacyPage() {
  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen">
        <section className="px-6 lg:px-8 py-24">
          <div className="max-w-3xl mx-auto prose-content">
            <h1 className="text-4xl font-bold text-white mb-2">Privacy Policy</h1>
            <p className="text-gray-500 text-sm mb-12">Last updated: July 2026</p>

            <div className="space-y-10 text-gray-300 leading-relaxed">
              <div>
                <h2 className="text-xl font-semibold text-white mb-3">1. Information we collect</h2>
                <p>
                  When you create an account, we collect your email address and any profile
                  information you provide. When you use the product, we store the queries you
                  submit and the responses returned, so your query history is available across
                  sessions. If you contact us, we store your name, email, and message.
                </p>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white mb-3">2. How we use your information</h2>
                <p>
                  We use your information to operate your account, provide the query history
                  feature, respond to support requests, and maintain the security and reliability
                  of the service. We do not sell your personal information.
                </p>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white mb-3">3. Where your data is stored</h2>
                <p>
                  Account and application data is stored with Supabase, our authentication and
                  database provider. Query content is also processed by our backend AI service to
                  generate a response.
                </p>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white mb-3">4. Your rights</h2>
                <p>
                  You can update your profile information or delete your account at any time from
                  your account settings. Deleting your account removes your profile and query
                  history.
                </p>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white mb-3">5. Contact</h2>
                <p>
                  Questions about this policy can be sent to{' '}
                  <a href="mailto:privacy@labeele.ai" className="text-gold-500 hover:text-gold-400">
                    privacy@labeele.ai
                  </a>
                  .
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  )
}
