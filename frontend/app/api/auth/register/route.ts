import { NextResponse } from 'next/server'
import { dukeFetch } from '@/lib/duke-server'
import { SESSION_COOKIE } from '@/lib/session'

// Thin proxy to the backend's own account system (see
// backend/coordinator_API/routers/accounts.py) - calls it server-to-server
// (no CORS/cross-site cookie issues) and turns the JWT it returns into an
// httpOnly cookie on this site's own origin.
export async function POST(request: Request) {
  const body = await request.json().catch(() => null)

  const res = await dukeFetch('/api/accounts/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).catch(() => null)

  if (!res) {
    return NextResponse.json({ error: 'Could not reach the backend. Please try again.' }, { status: 502 })
  }

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    return NextResponse.json({ error: data.detail || 'Sign-up failed.' }, { status: res.status })
  }

  const response = NextResponse.json({ user: data.user })
  response.cookies.set(SESSION_COOKIE, data.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30,
  })
  return response
}
