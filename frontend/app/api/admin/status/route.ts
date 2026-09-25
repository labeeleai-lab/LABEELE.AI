import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { SESSION_COOKIE, verifySessionToken } from '@/lib/session'

// Unlike other /api/admin/* routes, this doesn't require the caller to
// already be an admin - it just answers "am I one?" for the signed-in user,
// so the UI can decide whether to show an Admin link. Not a privileged read.
export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  const session = await verifySessionToken(token)

  return NextResponse.json({ isAdmin: Boolean(session?.is_admin) })
}
