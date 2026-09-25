import { NextResponse } from 'next/server'
import { dukeFetch } from '@/lib/duke-server'
import { SESSION_COOKIE } from '@/lib/session'

export async function POST(request: Request) {
  const body = await request.json().catch(() => null)

  const res = await dukeFetch('/api/accounts/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).catch(() => null)

  if (!res) {
    return NextResponse.json({ error: 'Could not reach the backend. Please try again.' }, { status: 502 })
  }

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    return NextResponse.json({ error: data.detail || 'Invalid email or password.' }, { status: res.status })
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
