'use client'

import { useEffect, useState } from 'react'
import { Loader2, UserPlus, Trash2, ShieldCheck } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'

interface AdminUser {
  email: string
  added_by: string | null
  created_at: string
}

export default function AdminTeamPage() {
  const [admins, setAdmins] = useState<AdminUser[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [newEmail, setNewEmail] = useState('')
  const [adding, setAdding] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  const loadAdmins = async () => {
    setLoadError(null)
    try {
      const res = await fetch('/api/admin/team')
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Failed to load admins')
      setAdmins(body.admins)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load admins')
    }
  }

  useEffect(() => {
    loadAdmins()
  }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setAdding(true)
    try {
      const res = await fetch('/api/admin/team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: newEmail }),
      })
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Failed to add admin')
      setNewEmail('')
      await loadAdmins()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to add admin')
    } finally {
      setAdding(false)
    }
  }

  const handleRemove = async (email: string) => {
    setRemoving(email)
    try {
      const res = await fetch(`/api/admin/team/${encodeURIComponent(email)}`, { method: 'DELETE' })
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Failed to remove admin')
      await loadAdmins()
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to remove admin')
    } finally {
      setRemoving(null)
    }
  }

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Team</h1>
      <p className="text-gray-400 mb-8">Manage who has access to this admin portal.</p>

      <div className="max-w-2xl space-y-6">
        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-4">Add an admin</h2>
          <form onSubmit={handleAdd} className="flex gap-3">
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="teammate@example.com"
              required
              className="flex-1 px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors"
            />
            <button
              type="submit"
              disabled={adding}
              className="flex items-center gap-2 px-5 py-2.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              Add
            </button>
          </form>
          {formError && (
            <p role="alert" className="mt-3 text-sm text-red-400">
              {formError}
            </p>
          )}
        </GlassCard>

        <GlassCard>
          <h2 className="text-lg font-semibold text-white mb-4">Current admins</h2>
          {loadError && <p className="text-red-400 text-sm mb-3">{loadError}</p>}
          {!admins ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : (
            <ul className="divide-y divide-gold-500/10">
              {admins.map((admin) => (
                <li key={admin.email} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-gold-500 shrink-0" />
                    <div>
                      <div className="text-sm text-white">{admin.email}</div>
                      <div className="text-xs text-gray-500">
                        Added {new Date(admin.created_at).toLocaleDateString()}
                        {admin.added_by ? ` by ${admin.added_by}` : ''}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(admin.email)}
                    disabled={removing === admin.email || admins.length <= 1}
                    title={admins.length <= 1 ? "Can't remove the last admin" : 'Remove admin'}
                    className="text-gray-500 hover:text-red-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {removing === admin.email ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      </div>
    </AdminShell>
  )
}
