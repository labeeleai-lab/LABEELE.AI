import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { DUKE_API_URL } from '@/lib/duke-api'
import { SESSION_COOKIE } from '@/lib/session'

// Dashboard "recent queries" - proxies to the backend with the caller's own
// session token as a Bearer credential (see lib/query-history.ts, the
// client-side wrapper that calls this).
async function getToken() {
  return (await cookies()).get(SESSION_COOKIE)?.value
}

export async function GET(request: Request) {
  const token = await getToken()
  if (!token) return NextResponse.json([], { status: 200 })

  const { searchParams } = new URL(request.url)
  const limit = searchParams.get('limit') ?? '20'

  const res = await fetch(`${DUKE_API_URL}/api/accounts/history?limit=${encodeURIComponent(limit)}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null)

  if (!res || !res.ok) return NextResponse.json([], { status: 200 })

  return NextResponse.json(await res.json())
}

export async function POST(request: Request) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Not signed in.' }, { status: 401 })

  const body = await request.json().catch(() => null)

  const res = await fetch(`${DUKE_API_URL}/api/accounts/history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    return NextResponse.json({ error: data.detail || 'Failed to save query.' }, { status: res.status })
  }

  return NextResponse.json({ success: true })
}
