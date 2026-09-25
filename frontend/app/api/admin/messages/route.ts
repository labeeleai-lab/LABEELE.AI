import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { dukeFetch } from '@/lib/duke-server'

const ADMIN_SECRET = process.env.DUKE_ADMIN_SECRET

export async function GET() {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const res = await dukeFetch('/api/accounts/admin/contact-messages', {
    headers: { 'X-Admin-Secret': ADMIN_SECRET },
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to load messages.' }, { status: res.status })

  return NextResponse.json({ messages: data })
}
