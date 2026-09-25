import 'server-only'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { SESSION_COOKIE, verifySessionToken } from './session'

// requireAdminUser() re-verifies the caller's own session cookie server-side
// (never trusts middleware alone) before letting a request into any
// /api/admin/* route handler - those can trigger retraining, delete data, or
// push commits to GitHub. is_admin is baked into the session token itself
// (see backend/coordinator_API/core/accounts_security.py), so this is a
// local, no-network-call check.
export async function requireAdminUser(): Promise<
  { user: { email: string } } | { errorResponse: NextResponse }
> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  const session = await verifySessionToken(token)

  if (!session || !session.is_admin) {
    return { errorResponse: NextResponse.json({ error: 'Forbidden' }, { status: 403 }) }
  }

  return { user: { email: session.email } }
}
