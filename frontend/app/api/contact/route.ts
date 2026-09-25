import { NextResponse } from 'next/server'
import { DUKE_API_URL } from '@/lib/duke-api'

// Public - proxies the contact form to the backend's local SQLite-backed
// contact_messages table (see backend/coordinator_API/routers/accounts.py).
// Read via the admin portal at /admin/messages.
export async function POST(request: Request) {
  const body = await request.json().catch(() => null)

  const res = await fetch(`${DUKE_API_URL}/api/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).catch(() => null)

  if (!res) {
    return NextResponse.json({ error: 'Could not reach the backend. Please try again.' }, { status: 502 })
  }

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    return NextResponse.json({ error: data.detail || 'Failed to send message.' }, { status: res.status })
  }

  return NextResponse.json({ success: true })
}
