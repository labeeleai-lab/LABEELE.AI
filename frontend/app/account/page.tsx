'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, Check, Trash2 } from 'lucide-react'
import AppShell from '../components/AppShell'
import GlassCard from '../components/GlassCard'
import PasswordInput from '../components/PasswordInput'
import { supabaseBrowser } from '@/lib/supabase/client'

const profileSchema = z.object({
  fullName: z.string().max(100).optional(),
})
type ProfileForm = z.infer<typeof profileSchema>

const passwordSchema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
type PasswordForm = z.infer<typeof passwordSchema>

export default function AccountPage() {
  const router = useRouter()
  const [email, setEmail] = useState<string | null>(null)
  const [profileSaved, setProfileSaved] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleted, setDeleted] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const profileFormApi = useForm<ProfileForm>({ resolver: zodResolver(profileSchema) })
  const passwordFormApi = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) })

  useEffect(() => {
    supabaseBrowser?.auth.getUser().then(({ data }) => {
      if (data.user) {
        setEmail(data.user.email ?? null)
        profileFormApi.reset({ fullName: (data.user.user_metadata?.full_name as string) ?? '' })
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onSaveProfile = async (values: ProfileForm) => {
    setProfileSaved(false)
    await supabaseBrowser?.auth.updateUser({ data: { full_name: values.fullName } })
    setProfileSaved(true)
  }

  const onChangePassword = async (values: PasswordForm) => {
    setPasswordError(null)
    setPasswordSaved(false)
    const { error } = await supabaseBrowser?.auth.updateUser({ password: values.password }) ?? {}
    if (error) {
      setPasswordError(error.message)
      return
    }
    setPasswordSaved(true)
    passwordFormApi.reset()
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirm !== email) return
    setDeleting(true)
    setDeleteError(null)

    try {
      const res = await fetch('/api/account/delete', { method: 'POST' })
      const body = await res.json()

      if (!res.ok) {
        setDeleteError(body.error || 'Something went wrong deleting your account.')
        return
      }

      setDeleted(true)
      setTimeout(() => router.push('/'), 2000)
    } catch {
      setDeleteError('Something went wrong deleting your account.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AppShell>
      <h1 className="text-3xl font-bold text-white mb-8">Account</h1>

      <div className="max-w-2xl space-y-6">
        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-5">Profile</h2>
          <form onSubmit={profileFormApi.handleSubmit(onSaveProfile)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <input
                type="email"
                value={email ?? ''}
                disabled
                className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/10 rounded-lg text-gray-400 cursor-not-allowed"
              />
            </div>
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-1.5">
                Display name
              </label>
              <input
                id="fullName"
                type="text"
                className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors"
                {...profileFormApi.register('fullName')}
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={profileFormApi.formState.isSubmitting}
                className="px-5 py-2.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50"
              >
                {profileFormApi.formState.isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
              </button>
              {profileSaved && (
                <span className="text-sm text-emerald-400 flex items-center gap-1.5">
                  <Check className="w-4 h-4" /> Saved
                </span>
              )}
            </div>
          </form>
        </GlassCard>

        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-5">Change password</h2>
          <form onSubmit={passwordFormApi.handleSubmit(onChangePassword)} className="space-y-4">
            {passwordError && (
              <div role="alert" className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
                {passwordError}
              </div>
            )}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
                New password
              </label>
              <PasswordInput id="password" autoComplete="new-password" {...passwordFormApi.register('password')} />
              {passwordFormApi.formState.errors.password && (
                <p role="alert" className="mt-1.5 text-sm text-red-400">
                  {passwordFormApi.formState.errors.password.message}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1.5">
                Confirm new password
              </label>
              <PasswordInput id="confirmPassword" autoComplete="new-password" {...passwordFormApi.register('confirmPassword')} />
              {passwordFormApi.formState.errors.confirmPassword && (
                <p role="alert" className="mt-1.5 text-sm text-red-400">
                  {passwordFormApi.formState.errors.confirmPassword.message}
                </p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={passwordFormApi.formState.isSubmitting}
                className="px-5 py-2.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50"
              >
                {passwordFormApi.formState.isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Update password'}
              </button>
              {passwordSaved && (
                <span className="text-sm text-emerald-400 flex items-center gap-1.5">
                  <Check className="w-4 h-4" /> Updated
                </span>
              )}
            </div>
          </form>
        </GlassCard>

        <GlassCard className="border-red-500/30">
          <h2 className="text-lg font-semibold text-red-400 mb-2 flex items-center gap-2">
            <Trash2 className="w-4 h-4" /> Delete account
          </h2>
          {deleted ? (
            <p className="text-gray-300 text-sm">
              Your account and all associated data have been permanently deleted. Redirecting home&hellip;
            </p>
          ) : (
            <>
              <p className="text-gray-400 text-sm mb-4">
                This permanently deletes your account and query history. This can&apos;t be undone.
              </p>
              {deleteError && (
                <div role="alert" className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
                  {deleteError}
                </div>
              )}
              <label className="block text-sm text-gray-400 mb-2">
                Type your email (<span className="text-gray-300">{email}</span>) to confirm
              </label>
              <input
                type="email"
                value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                className="w-full mb-4 px-4 py-2.5 bg-white/5 border border-red-500/30 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500 transition-colors"
              />
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirm !== email || deleting}
                className="px-5 py-2.5 bg-red-500/90 text-white font-semibold rounded-lg hover:bg-red-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Permanently delete my account'}
              </button>
            </>
          )}
        </GlassCard>
      </div>
    </AppShell>
  )
}
