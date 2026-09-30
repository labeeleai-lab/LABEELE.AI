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
import { PageHeader } from '../components/ui'

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
    fetch('/api/auth/profile')
      .then((res) => res.json())
      .then((data) => {
        if (data?.email) {
          setEmail(data.email)
          profileFormApi.reset({ fullName: data.full_name ?? '' })
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onSaveProfile = async (values: ProfileForm) => {
    setProfileSaved(false)
    await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: values.fullName }),
    })
    setProfileSaved(true)
  }

  const onChangePassword = async (values: PasswordForm) => {
    setPasswordError(null)
    setPasswordSaved(false)
    const res = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: values.password }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      setPasswordError(body.error || 'Failed to update password.')
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
      <PageHeader title="Account" description="Your profile, password, and account settings." />

      <div className="max-w-2xl space-y-6">
        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-5">Profile</h2>
          <form onSubmit={profileFormApi.handleSubmit(onSaveProfile)} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={email ?? ''}
                disabled
                className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/10 rounded-lg text-gray-400 cursor-not-allowed"
              />
            </div>
            <div>
              <label htmlFor="fullName" className="label">
                Display name
              </label>
              <input
                id="fullName"
                type="text"
                className="input w-full"
                {...profileFormApi.register('fullName')}
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={profileFormApi.formState.isSubmitting}
                className="btn btn-primary"
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
              <div role="alert" className="alert alert-error">
                {passwordError}
              </div>
            )}
            <div>
              <label htmlFor="password" className="label">
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
              <label htmlFor="confirmPassword" className="label">
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
                className="btn btn-primary"
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
                <div role="alert" className="alert mb-4 alert-error">
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
