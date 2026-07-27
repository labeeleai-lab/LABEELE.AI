'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, CheckCircle2, Mail } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

const contactSchema = z.object({
  name: z.string().min(1, 'Enter your name'),
  email: z.string().email('Enter a valid email address'),
  message: z.string().min(10, 'Tell us a bit more (at least 10 characters)'),
})

type ContactForm = z.infer<typeof contactSchema>

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ContactForm>({ resolver: zodResolver(contactSchema) })

  const onSubmit = async (values: ContactForm) => {
    setSubmitError(null)

    if (!isSupabaseConfigured || !supabaseBrowser) {
      setSubmitError('not_configured')
      return
    }

    const { error } = await supabaseBrowser.from('contact_messages').insert({
      name: values.name,
      email: values.email,
      message: values.message,
    })

    if (error) {
      setSubmitError(error.message)
      return
    }

    setSubmitted(true)
  }

  return (
    <>
      <SiteHeader />
      <main className="bg-royal-blue-900 min-h-screen px-6 lg:px-8 py-24">
        <div className="max-w-xl mx-auto">
          <h1 className="text-3xl lg:text-4xl font-bold text-white mb-3">Contact us</h1>
          <p className="text-gray-400 mb-10">
            Questions about the product, pricing, or a custom plan &mdash; send us a message and we&apos;ll
            get back to you.
          </p>

          <GlassCard>
            {submitted ? (
              <div className="flex flex-col items-center text-center py-8 gap-3">
                <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                <h2 className="text-xl font-semibold text-white">Message sent</h2>
                <p className="text-gray-400 text-sm">Thanks for reaching out &mdash; we&apos;ll reply by email soon.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    autoComplete="name"
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors"
                    {...register('name')}
                  />
                  {errors.name && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.name.message}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors"
                    {...register('email')}
                  />
                  {errors.email && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.email.message}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="message" className="block text-sm font-medium text-gray-300 mb-1.5">
                    Message
                  </label>
                  <textarea
                    id="message"
                    rows={5}
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors resize-none"
                    {...register('message')}
                  />
                  {errors.message && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.message.message}
                    </p>
                  )}
                </div>

                {submitError === 'not_configured' && (
                  <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg text-sm text-amber-200 flex items-start gap-2.5">
                    <Mail className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      The contact form isn&apos;t connected yet &mdash; email us directly at{' '}
                      <a href="mailto:hello@labeele.ai" className="underline">
                        hello@labeele.ai
                      </a>{' '}
                      instead.
                    </span>
                  </div>
                )}
                {submitError && submitError !== 'not_configured' && (
                  <div role="alert" className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
                    {submitError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send message'}
                </button>
              </form>
            )}
          </GlassCard>
        </div>
      </main>
      <SiteFooter />
    </>
  )
}
