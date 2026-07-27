'use client'

import { useState } from 'react'
import { MailCheck, Loader2 } from 'lucide-react'
import AuthShell from '../components/AuthShell'
import { supabaseBrowser, isSupabaseConfigured } from '@/lib/supabase/client'

export default function VerifyEmailPage() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const handleResend = async () => {
    setStatus('sending')
    setError(null)

    if (!isSupabaseConfigured || !supabaseBrowser || !email.trim()) {
      setStatus('error')
      setError(!email.trim() ? 'Enter your email first.' : 'Email sending isn’t configured yet.')
      return
    }

    const { error: resendError } = await supabaseBrowser.auth.resend({ type: 'signup', email: email.trim() })

    if (resendError) {
      setStatus('error')
      setError(resendError.message)
      return
    }

    setStatus('sent')
  }

  return (
    <AuthShell title="Verify your email" subtitle="Didn't get the link?">
      <div className="flex flex-col items-center text-center gap-5 py-2">
        <MailCheck className="w-10 h-10 text-gold-500" />
        <p className="text-gray-300 text-sm">
          Enter the email you signed up with and we&apos;ll send a new verification link.
        </p>

        <div className="w-full space-y-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors"
          />

          {status === 'sent' && (
            <p role="status" className="text-sm text-emerald-400">
              Verification email sent - check your inbox.
            </p>
          )}
          {status === 'error' && error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          <button
            onClick={handleResend}
            disabled={status === 'sending'}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'sending' ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Resend verification email'}
          </button>
        </div>
      </div>
    </AuthShell>
  )
}
