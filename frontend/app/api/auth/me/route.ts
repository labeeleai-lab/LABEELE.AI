import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { SESSION_COOKIE, verifySessionToken } from '@/lib/session'

// Fast path used on every page load (AppShell, dashboard, etc.) - verifies
// the session cookie locally, no network call to the backend at all, so the
// UI never has to wait on (or fail because of) the backend being slow/down.
export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  const session = await verifySessionToken(token)

  if (!session) {
    return NextResponse.json({ user: null })
  }

  return NextResponse.json({
    user: { email: session.email, isAdmin: session.is_admin },
  })
}
