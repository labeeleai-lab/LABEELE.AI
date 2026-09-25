import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { DUKE_API_URL } from '@/lib/duke-api'
import { SESSION_COOKIE } from '@/lib/session'

// Deletes the CALLING user's own account. The account id always comes from
// their own verified session token (the backend re-derives it from the
// Bearer token) - never from the request body - so this can't be used to
// delete an arbitrary account.
export async function POST() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) {
    return NextResponse.json({ error: 'Not signed in.' }, { status: 401 })
  }

  const res = await fetch(`${DUKE_API_URL}/api/accounts/me`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null)

  if (!res) {
    return NextResponse.json({ error: 'Could not reach the backend.' }, { status: 502 })
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    return NextResponse.json({ error: data.detail || 'Failed to delete account.' }, { status: res.status })
  }

  const response = NextResponse.json({ success: true })
  response.cookies.delete(SESSION_COOKIE)
  return response
}
