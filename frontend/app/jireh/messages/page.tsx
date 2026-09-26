'use client'

import { useEffect, useState } from 'react'
import { Loader2, Mail, MailOpen } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'

interface ContactMessage {
  id: string
  name: string
  email: string
  message: string
  is_read: boolean
  created_at: string
}

export default function AdminMessagesPage() {
  const [messages, setMessages] = useState<ContactMessage[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [markingRead, setMarkingRead] = useState<string | null>(null)

  const loadMessages = async () => {
    setLoadError(null)
    try {
      const res = await fetch('/api/admin/messages')
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Failed to load messages')
      setMessages(body.messages)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load messages')
    }
  }

  useEffect(() => {
    loadMessages()
  }, [])

  const handleMarkRead = async (id: string) => {
    setMarkingRead(id)
    try {
      await fetch(`/api/admin/messages/${id}/read`, { method: 'POST' })
      setMessages((prev) => prev?.map((m) => (m.id === id ? { ...m, is_read: true } : m)) ?? null)
    } finally {
      setMarkingRead(null)
    }
  }

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Messages</h1>
      <p className="text-gray-400 mb-8">Submissions from the site&apos;s contact form.</p>

      <div className="max-w-3xl">
        {loadError && <p className="text-red-400 text-sm mb-4">{loadError}</p>}

        {!messages ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
          </div>
        ) : messages.length === 0 ? (
          <p className="text-gray-400 text-sm">No messages yet.</p>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <GlassCard key={msg.id} className={msg.is_read ? 'opacity-60' : ''}>
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <div className="text-sm font-semibold text-white">{msg.name}</div>
                    <a href={`mailto:${msg.email}`} className="text-xs text-gold-500 hover:text-gold-400">
                      {msg.email}
                    </a>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-gray-500">{new Date(msg.created_at).toLocaleString()}</span>
                    <button
                      onClick={() => handleMarkRead(msg.id)}
                      disabled={msg.is_read || markingRead === msg.id}
                      title={msg.is_read ? 'Read' : 'Mark as read'}
                      className="text-gray-500 hover:text-gold-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                    >
                      {markingRead === msg.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : msg.is_read ? (
                        <MailOpen className="w-4 h-4" />
                      ) : (
                        <Mail className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{msg.message}</p>
              </GlassCard>
            ))}
          </div>
        )}
      </div>
    </AdminShell>
  )
}
