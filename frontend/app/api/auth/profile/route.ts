import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { DUKE_API_URL } from '@/lib/duke-api'
import { SESSION_COOKIE } from '@/lib/session'

// Full profile read/update (Account page only) - proxies to the backend
// with the caller's own session token as a Bearer credential, so the
// backend re-verifies identity itself rather than trusting anything the
// client sends.
async function getToken() {
  return (await cookies()).get(SESSION_COOKIE)?.value
}

export async function GET() {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Not signed in.' }, { status: 401 })

  const res = await fetch(`${DUKE_API_URL}/api/accounts/me`, {
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to load profile.' }, { status: res.status })

  return NextResponse.json(data)
}

export async function PUT(request: Request) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Not signed in.' }, { status: 401 })

  const body = await request.json().catch(() => null)

  const res = await fetch(`${DUKE_API_URL}/api/accounts/me`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Update failed.' }, { status: res.status })

  return NextResponse.json(data)
}
