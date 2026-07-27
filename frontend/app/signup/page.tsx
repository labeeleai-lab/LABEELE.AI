'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, MailCheck } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import PasswordInput from '../components/PasswordInput'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

const signupSchema = z
  .object({
    email: z.string().email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type SignupForm = z.infer<typeof signupSchema>

export default function SignupPage() {
  const [formError, setFormError] = useState<string | null>(null)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({ resolver: zodResolver(signupSchema) })

  const onSubmit = async (values: SignupForm) => {
    setFormError(null)

    if (!isSupabaseConfigured || !supabaseBrowser) {
      setFormError('Sign-up isn’t configured yet. Add Supabase credentials to enable it.')
      return
    }

    const { error } = await supabaseBrowser.auth.signUp({
      email: values.email,
      password: values.password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/dashboard`,
      },
    })

    if (error) {
      setFormError(error.message)
      setFocus('email')
      return
    }

    setSubmittedEmail(values.email)
  }

  if (submittedEmail) {
    return (
      <AuthShell title="Check your email" subtitle="One more step">
        <div className="flex flex-col items-center text-center gap-4 py-4">
          <MailCheck className="w-10 h-10 text-emerald-400" />
          <p className="text-gray-300 text-sm">
            We sent a verification link to <span className="text-white font-medium">{submittedEmail}</span>.
            Click it to activate your account, then log in.
          </p>
          <Link
            href="/login"
            className="mt-2 inline-flex items-center justify-center px-6 py-2.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors"
          >
            Go to login
          </Link>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start your 14-day free trial"
      footer={
        <>
          Already have an account?{' '}
          <Link href="/login" className="text-gold-500 hover:text-gold-400 font-medium">
            Log in
          </Link>
        </>
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

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
            Password
          </label>
          <PasswordInput id="password" autoComplete="new-password" {...register('password')} />
          {errors.password && (
            <p role="alert" className="mt-1.5 text-sm text-red-400">
              {errors.password.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1.5">
            Confirm password
          </label>
          <PasswordInput id="confirmPassword" autoComplete="new-password" {...register('confirmPassword')} />
          {errors.confirmPassword && (
            <p role="alert" className="mt-1.5 text-sm text-red-400">
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create account'}
        </button>

        <p className="text-xs text-gray-500 text-center">
          By signing up you agree to our{' '}
          <Link href="/terms" className="text-gold-500 hover:text-gold-400">Terms</Link> and{' '}
          <Link href="/privacy" className="text-gold-500 hover:text-gold-400">Privacy Policy</Link>.
        </p>
      </form>
    </AuthShell>
  )
}
