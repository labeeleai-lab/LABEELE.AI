'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, CheckCircle2 } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import PasswordInput from '../components/PasswordInput'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

const schema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type ResetPasswordForm = z.infer<typeof schema>

export default function ResetPasswordPage() {
  const router = useRouter()
  const [formError, setFormError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordForm>({ resolver: zodResolver(schema) })

  const onSubmit = async (values: ResetPasswordForm) => {
    setFormError(null)

    if (!isSupabaseConfigured || !supabaseBrowser) {
      setFormError('Password reset isn’t configured yet. Add Supabase credentials to enable it.')
      return
    }

    const { error } = await supabaseBrowser.auth.updateUser({ password: values.password })

    if (error) {
      setFormError(error.message)
      return
    }

    setDone(true)
    setTimeout(() => router.push('/dashboard'), 1500)
  }

  if (done) {
    return (
      <AuthShell title="Password updated" subtitle="You're all set">
        <div className="flex flex-col items-center text-center gap-4 py-4">
          <CheckCircle2 className="w-10 h-10 text-emerald-400" />
          <p className="text-gray-300 text-sm">Taking you to your dashboard&hellip;</p>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell title="Set a new password" subtitle="Choose something you haven't used before">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {formError && (
          <div role="alert" className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
            {formError}
          </div>
        )}

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
            New password
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
            Confirm new password
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
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Update password'}
        </button>
      </form>
    </AuthShell>
  )
}
