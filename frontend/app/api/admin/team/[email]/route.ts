import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { dukeFetch } from '@/lib/duke-server'

const ADMIN_SECRET = process.env.DUKE_ADMIN_SECRET

export async function DELETE(_request: Request, { params }: { params: Promise<{ email: string }> }) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const { email } = await params
  const targetEmail = decodeURIComponent(email).toLowerCase()

  const res = await dukeFetch(`/api/accounts/admin/users/${encodeURIComponent(targetEmail)}`, {
    method: 'DELETE',
    headers: { 'X-Admin-Secret': ADMIN_SECRET },
  }).catch(() => null)

  if (!res) return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) return NextResponse.json({ error: data.detail || 'Failed to remove admin.' }, { status: res.status })

  return NextResponse.json({ success: true })
}
