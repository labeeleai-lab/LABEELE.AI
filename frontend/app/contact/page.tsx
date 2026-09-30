'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, CheckCircle2, Mail, Phone } from 'lucide-react'
import SiteHeader from '../components/SiteHeader'
import SiteFooter from '../components/SiteFooter'
import GlassCard from '../components/GlassCard'

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

    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    })

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setSubmitError(body.error || 'Something went wrong sending your message.')
      return
    }

    setSubmitted(true)
  }

  return (
    <>
      <SiteHeader />
      <main className=" min-h-screen px-6 lg:px-8 py-24">
        <div className="max-w-xl mx-auto">
          <h1 className="text-3xl lg:text-4xl font-bold text-white mb-3">Contact us</h1>
          <p className="text-gray-400 mb-6">
            Questions about the product, pricing, or a custom plan &mdash; send us a message and we&apos;ll
            get back to you.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mb-10">
            <a
              href="mailto:labeeleai@gmail.com"
              className="flex items-center gap-2 text-sm text-gray-300 hover:text-gold-500 transition-colors"
            >
              <Mail className="w-4 h-4 text-gold-500" />
              labeeleai@gmail.com
            </a>
            <a
              href="tel:+12149311968"
              className="flex items-center gap-2 text-sm text-gray-300 hover:text-gold-500 transition-colors"
            >
              <Phone className="w-4 h-4 text-gold-500" />
              (214) 931-1968
            </a>
          </div>

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
                  <label htmlFor="name" className="label">
                    Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    autoComplete="name"
                    className="input w-full"
                    {...register('name')}
                  />
                  {errors.name && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.name.message}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="email" className="label">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    className="input w-full"
                    {...register('email')}
                  />
                  {errors.email && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.email.message}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="message" className="label">
                    Message
                  </label>
                  <textarea
                    id="message"
                    rows={5}
                    className="input w-full resize-none"
                    {...register('message')}
                  />
                  {errors.message && (
                    <p role="alert" className="mt-1.5 text-sm text-red-400">
                      {errors.message.message}
                    </p>
                  )}
                </div>

                {submitError && (
                  <div role="alert" className="alert alert-error">
                    {submitError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary btn-lg w-full"
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
