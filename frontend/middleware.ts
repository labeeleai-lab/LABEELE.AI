import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE, verifySessionToken } from './lib/session'

// This file must live at the project root (next to package.json) - Next.js silently
// ignores middleware.ts placed anywhere else, including inside app/, which is why
// /dashboard was previously reachable with no authentication at all.

const PROTECTED_PREFIXES = ['/dashboard', '/account', '/jireh']
const AUTH_PAGES = ['/login', '/signup']

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  const isProtected = PROTECTED_PREFIXES.some((prefix) => path.startsWith(prefix))
  const isAuthPage = AUTH_PAGES.includes(path)

  if (!isProtected && !isAuthPage) return NextResponse.next()

  // is_admin is baked into the session token itself (see
  // backend/coordinator_API/core/accounts_security.py), so this whole check
  // is a local JWT verify - no network call to the backend on every request.
  const session = await verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value)

  if (isProtected && !session) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('redirect', path)
    return NextResponse.redirect(url)
  }

  if (path.startsWith('/jireh') && session && !session.is_admin) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  if (isAuthPage && session) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/account/:path*', '/jireh/:path*', '/login', '/signup'],
}
