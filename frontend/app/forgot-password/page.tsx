'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, MailCheck } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
})

type ForgotPasswordForm = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [formError, setFormError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordForm>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: ForgotPasswordForm) => {
    setFormError(null)

    if (!isSupabaseConfigured || !supabaseBrowser) {
      setFormError('Password reset isn’t configured yet. Add Supabase credentials to enable it.')
      return
    }

    const { error } = await supabaseBrowser.auth.resetPasswordForEmail(values.email, {
      redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
    })

    // Supabase intentionally doesn't reveal whether the email exists - show the same
    // success state either way to avoid leaking which emails have accounts.
    if (error) {
      setFormError(error.message)
      return
    }

    setSent(true)
  }

  if (sent) {
    return (
      <AuthShell title="Check your email" subtitle="Password reset requested">
        <div className="flex flex-col items-center text-center gap-4 py-4">
          <MailCheck className="w-10 h-10 text-emerald-400" />
          <p className="text-gray-300 text-sm">
            If an account exists for that email, we&apos;ve sent a link to reset your password.
          </p>
          <Link href="/login" className="text-gold-500 hover:text-gold-400 text-sm font-medium">
            Back to login
          </Link>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title="Forgot your password?"
      subtitle="We'll email you a link to reset it"
      footer={
        <Link href="/login" className="text-gold-500 hover:text-gold-400 font-medium">
          Back to login
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {formError && (
          <div role="alert" className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
            {formError}
          </div>
        )}

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

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send reset link'}
        </button>
      </form>
    </AuthShell>
  )
}
