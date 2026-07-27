import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// This file must live at the project root (next to package.json) - Next.js silently
// ignores middleware.ts placed anywhere else, including inside app/, which is why
// /dashboard was previously reachable with no authentication at all.

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

const PROTECTED_PREFIXES = ['/dashboard', '/account']
const AUTH_PAGES = ['/login', '/signup']

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request })

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    // Supabase isn't configured - fail open rather than lock everyone out, but this
    // means auth isn't actually enforced yet. Set NEXT_PUBLIC_SUPABASE_URL/ANON_KEY.
    return response
  }

  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return request.cookies.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
        response = NextResponse.next({ request })
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options))
      },
    },
  })

  const {
    data: { user },
  } = await supabase.auth.getUser()

  const path = request.nextUrl.pathname
  const isProtected = PROTECTED_PREFIXES.some((prefix) => path.startsWith(prefix))
  const isAuthPage = AUTH_PAGES.includes(path)

  if (isProtected && !user) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('redirect', path)
    return NextResponse.redirect(url)
  }

  if (isAuthPage && user) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  return response
}

export const config = {
  matcher: ['/dashboard/:path*', '/account/:path*', '/login', '/signup'],
}
