import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { DUKE_API_URL } from '@/lib/duke-api'

const ADMIN_SECRET = process.env.DUKE_ADMIN_SECRET

export async function GET() {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const res = await fetch(`${DUKE_API_URL}/api/accounts/admin/users`, {
    headers: { 'X-Admin-Secret': ADMIN_SECRET },
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to load admins.' }, { status: res.status })

  return NextResponse.json({ admins: data })
}

export async function POST(request: Request) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const body = await request.json().catch(() => null)
  const email = typeof body?.email === 'string' ? body.email.trim().toLowerCase() : ''

  if (!email || !email.includes('@')) {
    return NextResponse.json({ error: 'Enter a valid email address.' }, { status: 422 })
  }

  const res = await fetch(`${DUKE_API_URL}/api/accounts/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': ADMIN_SECRET },
    body: JSON.stringify({ email }),
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to add admin.' }, { status: res.status })

  return NextResponse.json({ success: true }, { status: 201 })
}
