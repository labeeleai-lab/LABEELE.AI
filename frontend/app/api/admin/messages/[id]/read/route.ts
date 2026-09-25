import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { DUKE_API_URL } from '@/lib/duke-api'

const ADMIN_SECRET = process.env.DUKE_ADMIN_SECRET

export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const { id } = await params

  const res = await fetch(`${DUKE_API_URL}/api/accounts/admin/contact-messages/${encodeURIComponent(id)}/read`, {
    method: 'POST',
    headers: { 'X-Admin-Secret': ADMIN_SECRET },
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to update message.' }, { status: res.status })

  return NextResponse.json({ success: true })
}
