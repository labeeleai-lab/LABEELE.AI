'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import PasswordInput from '../components/PasswordInput'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})

type LoginForm = z.infer<typeof loginSchema>

function LoginFormInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (values: LoginForm) => {
    setFormError(null)

    if (!isSupabaseConfigured || !supabaseBrowser) {
      setFormError('Sign-in isn’t configured yet. Add Supabase credentials to enable it.')
      return
    }

    const { error } = await supabaseBrowser.auth.signInWithPassword(values)

    if (error) {
      setFormError(error.message)
      setFocus('email')
      return
    }

    router.push(searchParams.get('redirect') || '/dashboard')
    router.refresh()
  }

  return (
    <AuthShell
      title="Log in"
      subtitle="Welcome back to LABEELE.AI"
      footer={
        <>
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-gold-500 hover:text-gold-400 font-medium">
            Sign up
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
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="password" className="block text-sm font-medium text-gray-300">
              Password
            </label>
            <Link href="/forgot-password" className="text-xs text-gold-500 hover:text-gold-400">
              Forgot password?
            </Link>
          </div>
          <PasswordInput id="password" autoComplete="current-password" {...register('password')} />
          {errors.password && (
            <p role="alert" className="mt-1.5 text-sm text-red-400">
              {errors.password.message}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Log in'}
        </button>
      </form>
    </AuthShell>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginFormInner />
    </Suspense>
  )
}
